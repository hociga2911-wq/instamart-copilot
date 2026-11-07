
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agent import run_agent

SCENARIOS_FILE = ROOT / "data" / "raw" / "agent_scenarios.csv"
RESULTS_FILE = ROOT / "outputs" / "agent_evaluation.csv"

with SCENARIOS_FILE.open(
    newline="", encoding="utf-8"
) as file:
    scenarios = list(csv.DictReader(file))

results = []

for scenario in scenarios:
    scenario_id = scenario["scenario_id"]

    # Use a fresh run ID. Run this evaluation script only once
    # after resetting the Part D logs and state.
    run_id = f"evaluation_final_{scenario_id}"

    result = run_agent(
        user_message=scenario["message"],
        scenario_id=scenario_id,
        run_id=run_id
    )

    expected = scenario["expected_outcome"]
    expected_refund = float(scenario["expected_refund_inr"])

    answer = result["final_answer"]
    actual_status = result["status"]

    if expected == "FALLBACK":
        status_match = actual_status.startswith("FALLBACK")
    else:
        status_match = actual_status == expected

    actual_refund = 0.0

    # Read the amount from the actual tool observation.
    steps = result["steps"]

    for step in steps:
        observation = step.get("observation", {})

        if step.get("tool") in (
            "issue_refund",
            "escalate_to_human"
        ):
            actual_refund = float(
                observation.get("refund_inr", 0.0)
            )

    refund_match = abs(actual_refund - expected_refund) <= 0.01
    passed = status_match and refund_match

    results.append({
        "scenario_id": scenario_id,
        "expected_outcome": expected,
        "actual_status": actual_status,
        "expected_refund_inr": f"{expected_refund:.2f}",
        "actual_refund_inr": f"{actual_refund:.2f}",
        "llm_calls": result["llm_calls"],
        "tokens_used": result["tokens_used"],
        "steps": json.dumps(result["steps"]),
        "passed": passed,
        "final_answer": answer
    })

    print(
        f"{scenario_id}: expected={expected}, "
        f"actual={actual_status}, "
        f"refund=INR {actual_refund:.2f}, "
        f"calls={result['llm_calls']}, "
        f"tokens={result['tokens_used']}, "
        f"PASS={passed}"
    )

RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

with RESULTS_FILE.open(
    "w", newline="", encoding="utf-8"
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=list(results[0].keys())
    )
    writer.writeheader()
    writer.writerows(results)

passed_count = sum(row["passed"] for row in results)

print()
print(f"Evaluation complete: {passed_count}/{len(results)} passed.")
print(f"Results saved to: {RESULTS_FILE}")