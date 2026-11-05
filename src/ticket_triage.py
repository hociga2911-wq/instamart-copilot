
import json
import random
import re
import time
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================


# Allow Python to import mock_llm.py from the project root.

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mock_llm

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "outputs"

TICKETS_FILE = RAW_DIR / "tickets.csv"
SEGMENTS_FILE = OUTPUT_DIR / "customer_segments.csv"
OUTPUT_DIR = ROOT / "outputs"

TICKETS_FILE = RAW_DIR / "tickets.csv"
SEGMENTS_FILE = OUTPUT_DIR / "customer_segments.csv"

ZERO_BUDGET = 6000
FINAL_BUDGET = 100000
MAX_RETRIES = 3

ALLOWED_CATEGORIES = {"billing", "delivery", "technical", "fraud"}

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_PATTERN = re.compile(r"\b[6-9]\d{9}\b")
ORDER_PATTERN = re.compile(r"ORD-\d{6}")


# ============================================================
# PROMPTS
# ============================================================

ZERO_SHOT_SYSTEM = """
You are a customer support ticket classifier.
CLASSIFY each customer support ticket into exactly one category:
billing, delivery, technical, or fraud.

Return JSON only, with exactly these keys:
{"category": "...", "reason": "..."}

The category must be one of the four allowed categories.
Do not include markdown or any text outside the JSON object.
""".strip()


FEW_SHOT_SYSTEM = """
You are a customer support ticket classifier.
CLASSIFY each customer support ticket into exactly one category:
billing, delivery, technical, or fraud.

Return JSON only, with exactly these keys:
{"category": "...", "reason": "..."}

The category must be one of the four allowed categories.
Do not include markdown or any text outside the JSON object.

EXAMPLES:
Ticket: Someone accessed my account without permission.
{"category": "fraud", "reason": "Unauthorized account access"}

Ticket: My payment was deducted twice.
{"category": "billing", "reason": "Duplicate payment deduction"}

Ticket: The delivery is late and the rider has not arrived.
{"category": "delivery", "reason": "Late delivery"}
""".strip()


# ============================================================
# REDACTION
# ============================================================

def redact_text(text: str) -> tuple[str, dict]:
    """Redact email, phone, and order ID using the required order."""

    result = text or ""

    result, email_count = EMAIL_PATTERN.subn("[EMAIL]", result)
    result, phone_count = PHONE_PATTERN.subn("[PHONE]", result)
    result, order_count = ORDER_PATTERN.subn("[ORDER_ID]", result)

    counts = {
        "email": email_count,
        "phone": phone_count,
        "order_id": order_count,
    }

    return result, counts


def count_remaining_pii(text: str) -> int:
    """Count any remaining matches for the specified PII patterns."""

    return (
        len(EMAIL_PATTERN.findall(text))
        + len(PHONE_PATTERN.findall(text))
        + len(ORDER_PATTERN.findall(text))
    )


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def validate_model_output(content: str) -> tuple[str, str, str]:
    """
    Returns:
        status, category, reason

    Valid JSON with an allowed category -> classified_json
    Non-JSON output with exactly one allowed category word
        -> classified_keyword
    Everything else -> flagged_invalid_output
    """

    content = content or ""

    try:
        parsed = json.loads(content)

        if not isinstance(parsed, dict):
            return "flagged_invalid_output", "", ""

        category = parsed.get("category")

        # Valid JSON with an invalid category must not fall
        # through to keyword matching.
        if not isinstance(category, str):
            return "flagged_invalid_output", "", ""

        category = category.strip().lower()

        if category not in ALLOWED_CATEGORIES:
            return "flagged_invalid_output", "", ""

        reason = parsed.get("reason", "")
        if not isinstance(reason, str):
            reason = str(reason)

        return "classified_json", category, reason

    except (json.JSONDecodeError, TypeError, ValueError):
        words = re.findall(r"[a-z]+", content.lower())
        found = set(words) & ALLOWED_CATEGORIES

        if len(found) == 1:
            category = next(iter(found))
            return "classified_keyword", category, "Recovered from keyword"

        return "flagged_invalid_output", "", ""


# ============================================================
# MODEL CALL WITH RETRIES
# ============================================================

def call_with_retries(
    messages: list[dict],
    ticket_id: str,
    budget_state: dict | None = None,
    token_budget: int | None = None,
):
    """
    Calls the mock model with up to MAX_RETRIES retries.

    The budget is checked immediately before every model call.
    A transient exception consumes no reported model tokens.
    """

    for retry_number in range(MAX_RETRIES + 1):

        if (
            budget_state is not None
            and token_budget is not None
            and budget_state["tokens"] >= token_budget
        ):
            return None, "budget_exhausted"

        try:
            response = mock_llm.chat(messages)

            used = response.usage.total_tokens

            if budget_state is not None:
                budget_state["tokens"] += used

            return response, "success"

        except mock_llm.TransientLLMError:
            if retry_number >= MAX_RETRIES:
                return None, "retry_exhausted"

            wait_seconds = (
                0.05
                * (2 ** retry_number)
                * random.uniform(0.9, 1.15)
            )

            print(
                f"ticket_id={ticket_id} "
                f"retry={retry_number} "
                f"wait={wait_seconds:.4f}s"
            )

            time.sleep(wait_seconds)

    return None, "retry_exhausted"


# ============================================================
# ONE COMPLETE TRIAGE RUN
# ============================================================

def run_triage(
    tickets: pd.DataFrame,
    system_prompt: str,
    token_budget: int | None = None,
    run_name: str = "triage",
) -> tuple[pd.DataFrame, dict]:

    # Required: reset immediately before each complete run.
    mock_llm.reset()

    budget_state = {"tokens": 0}

    results = []
    total_redactions = {
        "email": 0,
        "phone": 0,
        "order_id": 0,
    }

    eligible_count = 0
    model_call_count = 0
    retry_exhausted_count = 0

    for _, row in tickets.iterrows():

        ticket_id = str(row["ticket_id"])
        raw_text = "" if pd.isna(row["text"]) else str(row["text"])

        base = {
            "ticket_id": ticket_id,
            "customer_id": row["customer_id"],
            "status": "",
            "category": "",
            "reason": "",
            "tokens_used": 0,
            "true_category": str(row["true_category"]).strip().lower(),
        }

        # Guardrail 1: empty or whitespace-only input.
        if not raw_text.strip():
            base["status"] = "skipped_empty"
            results.append(base)
            continue

        # Guardrail 2: long input. No model call.
        estimated_tokens = mock_llm.est_tokens(raw_text)

        if estimated_tokens > 400:
            base["status"] = "flagged_long"
            results.append(base)
            continue

        eligible_count += 1

        # Redact before the text can be sent to the model.
        redacted_text, counts = redact_text(raw_text)

        for key in total_redactions:
            total_redactions[key] += counts[key]

        # Verify the redacted message has none of the specified PII.
        if count_remaining_pii(redacted_text) != 0:
            raise AssertionError(
                f"PII remained after redaction for ticket {ticket_id}"
            )

        # The user message must contain exactly the redacted ticket text.
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": redacted_text},
        ]

        response, call_status = call_with_retries(
            messages=messages,
            ticket_id=ticket_id,
            budget_state=budget_state,
            token_budget=token_budget,
        )

        if call_status == "budget_exhausted":
            base["status"] = "budget_exhausted"
            results.append(base)
            continue

        if call_status == "retry_exhausted":
            base["status"] = "flagged_invalid_output"
            retry_exhausted_count += 1
            results.append(base)
            continue

        model_call_count += 1

        base["tokens_used"] = response.usage.total_tokens

        content = response.choices[0].message.content or ""

        status, category, reason = validate_model_output(content)

        base["status"] = status
        base["category"] = category
        base["reason"] = reason

        results.append(base)

    result_df = pd.DataFrame(results)

    classified = result_df[
        result_df["status"].isin(["classified_json", "classified_keyword"])
    ]

    classified_count = len(classified)

    correct_count = (
        int((classified["category"] == classified["true_category"]).sum())
        if classified_count
        else 0
    )

    accuracy = (
        accuracy_score(classified["true_category"], classified["category"])
        if classified_count
        else 0.0
    )

    classified_tokens = int(classified["tokens_used"].sum())

    summary = {
        "run_name": run_name,
        "input_rows": len(tickets),
        "eligible_rows": eligible_count,
        "classified_json": int(
            (result_df["status"] == "classified_json").sum()
        ),
        "classified_keyword": int(
            (result_df["status"] == "classified_keyword").sum()
        ),
        "flagged_invalid_output": int(
            (result_df["status"] == "flagged_invalid_output").sum()
        ),
        "skipped_empty": int(
            (result_df["status"] == "skipped_empty").sum()
        ),
        "flagged_long": int(
            (result_df["status"] == "flagged_long").sum()
        ),
        "budget_exhausted": int(
            (result_df["status"] == "budget_exhausted").sum()
        ),
        "retry_exhausted": retry_exhausted_count,
        "model_responses": model_call_count,
        "accuracy_on_classified": float(accuracy),
        "correct_classifications": correct_count,
        "classified_count": classified_count,
        "total_tokens_all_successful_responses": int(budget_state["tokens"]),
        "tokens_for_classified_tickets": classified_tokens,
        "average_tokens_per_classified_ticket": (
            classified_tokens / classified_count if classified_count else 0
        ),
        "redactions": total_redactions,
    }

    return result_df, summary


# ============================================================
# ROUTING
# ============================================================

def apply_routing(
    result_df: pd.DataFrame,
    segments: pd.DataFrame,
) -> pd.DataFrame:

    segment_lookup = (
        segments[["customer_id", "segment_name", "is_premium"]]
        .drop_duplicates("customer_id")
        .copy()
    )

    merged = result_df.merge(
        segment_lookup,
        on="customer_id",
        how="left",
    )

    merged["segment_name"] = merged["segment_name"].fillna("")
    merged["is_premium"] = merged["is_premium"].fillna(False).astype(bool)

    def route_row(row):

        status = row["status"]
        category = row["category"]

        # These cases must always go to human review.
        if status in {
            "skipped_empty",
            "flagged_long",
            "flagged_invalid_output",
            "budget_exhausted",
        }:
            return "human_review", "NORMAL"

        if status == "classified_json" or status == "classified_keyword":

            if category == "fraud":
                return "security_team", "HIGH"

            if row["is_premium"]:
                return "premium_desk", "HIGH"

            return "support_queue", "NORMAL"

        # Safe fallback for any unexpected status.
        return "human_review", "NORMAL"

    routed = merged.apply(route_row, axis=1, result_type="expand")
    merged["route"] = routed[0]
    merged["priority"] = routed[1]

    return merged


# ============================================================
# REPORTING
# ============================================================

def print_summary(summary: dict):
    print("\n" + "=" * 65)
    print(f"RUN SUMMARY: {summary['run_name']}")
    print("=" * 65)

    for key, value in summary.items():
        if key != "redactions":
            print(f"{key}: {value}")

    print("redactions:", summary["redactions"])


def print_zero_shot_confusion(result_df: pd.DataFrame):

    classified = result_df[
        result_df["status"].isin(["classified_json", "classified_keyword"])
    ]

    labels = ["billing", "delivery", "technical", "fraud"]

    matrix = confusion_matrix(
        classified["true_category"],
        classified["category"],
        labels=labels,
    )

    print("\nZero-shot confusion matrix")
    print("Label order:", labels)
    print(matrix)


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading ticket data...")
    tickets = pd.read_csv(TICKETS_FILE)

    required_columns = {
        "ticket_id",
        "customer_id",
        "order_id",
        "text",
        "true_category",
    }

    missing = required_columns - set(tickets.columns)

    if missing:
        raise ValueError(f"Missing ticket columns: {sorted(missing)}")

    print("Ticket rows:", len(tickets))

    # --------------------------------------------------------
    # 1. ZERO-SHOT RUN
    # --------------------------------------------------------

    zero_results, zero_summary = run_triage(
        tickets=tickets,
        system_prompt=ZERO_SHOT_SYSTEM,
        token_budget=None,
        run_name="zero_shot",
    )

    print_summary(zero_summary)
    print_zero_shot_confusion(zero_results)

    # Save a compact comparison file without raw ticket text.
    zero_results.to_csv(
        OUTPUT_DIR / "triage_zero_shot.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 2. FEW-SHOT RUN
    # --------------------------------------------------------

    few_results, few_summary = run_triage(
        tickets=tickets,
        system_prompt=FEW_SHOT_SYSTEM,
        token_budget=None,
        run_name="few_shot",
    )

    print_summary(few_summary)

    few_results.to_csv(
        OUTPUT_DIR / "triage_few_shot.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 3. ZERO-SHOT TOKEN BUDGET DEMONSTRATION
    # --------------------------------------------------------

    budget_results, budget_summary = run_triage(
        tickets=tickets,
        system_prompt=ZERO_SHOT_SYSTEM,
        token_budget=ZERO_BUDGET,
        run_name="zero_shot_budget_demo",
    )

    print_summary(budget_summary)

    budget_segments = pd.read_csv(SEGMENTS_FILE)

    budget_routed = apply_routing(
        budget_results,
        budget_segments,
    )

    budget_output_columns = [
        "ticket_id",
        "customer_id",
        "status",
        "category",
        "segment_name",
        "priority",
        "route",
        "tokens_used",
    ]

    budget_routed[budget_output_columns].to_csv(
        OUTPUT_DIR / "triage_budget_demo.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 4. FINAL FEW-SHOT RUN WITH LARGE TOKEN BUDGET
    # --------------------------------------------------------

    final_results, final_summary = run_triage(
        tickets=tickets,
        system_prompt=FEW_SHOT_SYSTEM,
        token_budget=FINAL_BUDGET,
        run_name="few_shot_final",
    )

    print_summary(final_summary)

    final_routed = apply_routing(
        final_results,
        budget_segments,
    )

    final_output_columns = [
        "ticket_id",
        "customer_id",
        "status",
        "category",
        "segment_name",
        "priority",
        "route",
        "tokens_used",
    ]

    final_output = final_routed[final_output_columns].copy()

    final_output.to_csv(
        OUTPUT_DIR / "triage_results.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 5. COMPARISON REPORT
    # --------------------------------------------------------

    comparison = pd.DataFrame([
        {
            "prompt": "zero_shot",
            "classified": zero_summary["classified_count"],
            "accuracy": zero_summary["accuracy_on_classified"],
            "total_tokens": zero_summary[
                "total_tokens_all_successful_responses"
            ],
            "average_tokens_per_classified": zero_summary[
                "average_tokens_per_classified_ticket"
            ],
        },
        {
            "prompt": "few_shot",
            "classified": few_summary["classified_count"],
            "accuracy": few_summary["accuracy_on_classified"],
            "total_tokens": few_summary[
                "total_tokens_all_successful_responses"
            ],
            "average_tokens_per_classified": few_summary[
                "average_tokens_per_classified_ticket"
            ],
        },
    ])

    comparison.to_csv(
        OUTPUT_DIR / "triage_prompt_comparison.csv",
        index=False,
    )

    # --------------------------------------------------------
    # 6. FINAL CHECKS
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("FINAL PART C CHECKS")
    print("=" * 65)

    assert len(final_output) == 164, (
        f"Expected 164 output rows, found {len(final_output)}"
    )

    assert list(final_output.columns) == final_output_columns

    assert final_summary["eligible_rows"] == 156

    assert final_summary["skipped_empty"] == 4
    assert final_summary["flagged_long"] == 4

    assert final_summary["classified_json"] == 135
    assert final_summary["classified_keyword"] == 12
    assert final_summary["flagged_invalid_output"] == 9

    assert final_summary["redactions"]["email"] == 55
    assert final_summary["redactions"]["phone"] == 91
    assert final_summary["redactions"]["order_id"] == 132

    assert final_summary["retry_exhausted"] == 0

    assert final_summary["budget_exhausted"] == 0

    assert budget_summary["budget_exhausted"] > 0

    assert final_summary["accuracy_on_classified"] == 1.0

    assert zero_summary["classified_count"] == 147
    assert few_summary["classified_count"] == 147

    print("Final output rows:", len(final_output))
    print("Final few-shot accuracy:", final_summary["accuracy_on_classified"])
    print("Budget-demo exhausted tickets:", budget_summary["budget_exhausted"])
    print("Final routing counts:")
    print(final_output["route"].value_counts())

    print("\nCreated files:")
    for filename in [
        "triage_zero_shot.csv",
        "triage_few_shot.csv",
        "triage_budget_demo.csv",
        "triage_results.csv",
        "triage_prompt_comparison.csv",
    ]:
        path = OUTPUT_DIR / filename
        print(f"{path.name}: {path.exists()}")

    print("\nAll Part C assertions passed.")


if __name__ == "__main__":
    main()
