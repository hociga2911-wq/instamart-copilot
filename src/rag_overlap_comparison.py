
"""Compare RAG evaluation with chunk overlap 10 versus overlap 0."""

import sys
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import rag_policy
import mock_llm

POLICY_DIR = ROOT / "data" / "policies"
EVAL_FILE = ROOT / "data" / "raw" / "policy_eval.csv"
OUTPUT_DIR = ROOT / "outputs"

BASELINE_FILE = OUTPUT_DIR / "rag_evaluation.csv"
OVERLAP0_FILE = OUTPUT_DIR / "rag_evaluation_overlap0.csv"


def build_zero_overlap_index():
    documents = rag_policy.load_policy_documents()
    chunks = []

    for filename, text in documents.items():
        pieces = rag_policy.split_into_chunks(
            text,
            chunk_size=40,
            overlap=0
        )

        for chunk_number, chunk_text in enumerate(pieces, start=1):
            chunks.append({
                "source": filename,
                "chunk_id": chunk_number,
                "text": chunk_text
            })

    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(
        [chunk["text"] for chunk in chunks]
    )

    return chunks, vectorizer, matrix


def retrieve_zero_overlap(query, chunks, vectorizer, matrix, k=3):
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, matrix).flatten()
    indices = scores.argsort()[::-1][:k]

    return [
        {
            **chunks[index],
            "score": float(scores[index])
        }
        for index in indices
    ]


def evaluate_zero_overlap():
    chunks, vectorizer, matrix = build_zero_overlap_index()
    evaluation = pd.read_csv(EVAL_FILE).fillna("")

    results = []

    for _, row in evaluation.iterrows():
        question = str(row["question"])
        expected_doc = str(row["expected_doc"])
        expected_fact = str(row["expected_fact"])

        retrieved = retrieve_zero_overlap(
            question, chunks, vectorizer, matrix, k=3
        )

        context = "\n".join(
            f"[{item['source']}] {item['text']}"
            for item in retrieved
        )

        messages = [
            {
                "role": "system",
                "content": rag_policy.SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"CONTEXT:\n{context}\n"
                    f"QUESTION:\n{question}"
                )
            }
        ]

        response = mock_llm.chat(messages)
        answer_text = response.choices[0].message.content

        sources = list(dict.fromkeys(
            item["source"] for item in retrieved
        ))

        is_unanswerable = expected_doc == "NONE"

        if is_unanswerable:
            doc_correct = None
            fact_correct = None
            fallback_correct = answer_text.startswith(
                "I could not find"
            )
        else:
            doc_correct = expected_doc in sources
            fact_correct = expected_fact in answer_text
            fallback_correct = None

        results.append({
            "question": question,
            "expected_doc": expected_doc,
            "expected_fact": expected_fact,
            "answer": answer_text,
            "sources": ", ".join(sources),
            "document_correct": doc_correct,
            "fact_correct": fact_correct,
            "fallback_correct": fallback_correct
        })

    results_df = pd.DataFrame(results)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OVERLAP0_FILE, index=False)

    answerable = results_df[
        results_df["expected_doc"] != "NONE"
    ]
    unanswerable = results_df[
        results_df["expected_doc"] == "NONE"
    ]

    print("\n========== ZERO-OVERLAP EVALUATION ==========")
    print("Chunk size: 40")
    print("Chunk overlap: 0")
    print("Total chunks:", len(chunks))
    print("Answerable:", len(answerable))
    print("Unanswerable:", len(unanswerable))
    print(
        "Document retrieval:",
        f"{answerable['document_correct'].sum()}/{len(answerable)}"
    )
    print(
        "Expected fact accuracy:",
        f"{answerable['fact_correct'].sum()}/{len(answerable)}"
    )
    print(
        "Correct fallback responses:",
        f"{unanswerable['fallback_correct'].sum()}/{len(unanswerable)}"
    )

    print("\nChunk distribution:")
    distribution = pd.Series(
        [chunk["source"] for chunk in chunks]
    ).value_counts().sort_index()
    print(distribution.to_string())

    print("\nAnswerable questions with incorrect facts:")
    failed = answerable[
        ~answerable["fact_correct"].astype(bool)
    ]

    if failed.empty:
        print("None")
    else:
        for _, row in failed.iterrows():
            print("\nQuestion:", row["question"])
            print("Expected fact:", row["expected_fact"])
            print("Actual answer:", row["answer"])

    print("\nSaved:", OVERLAP0_FILE)

    return results_df


def compare_results(zero_results):
    if not BASELINE_FILE.exists():
        print("\nBaseline file not found:", BASELINE_FILE)
        return

    baseline = pd.read_csv(BASELINE_FILE).fillna("")
    zero = zero_results.fillna("")

    baseline_answerable = baseline[
        baseline["expected_doc"] != "NONE"
    ]
    zero_answerable = zero[
        zero["expected_doc"] != "NONE"
    ]

    baseline_doc = int(
        baseline_answerable["document_correct"].astype(bool).sum()
    )
    zero_doc = int(
        zero_answerable["document_correct"].astype(bool).sum()
    )

    baseline_fact = int(
        baseline_answerable["fact_correct"].astype(bool).sum()
    )
    zero_fact = int(
        zero_answerable["fact_correct"].astype(bool).sum()
    )

    print("\n========== OVERLAP COMPARISON ==========")
    print("Metric                  Overlap 10    Overlap 0")
    print(
        f"Document retrieval      {baseline_doc}/12"
        f"          {zero_doc}/12"
    )
    print(
        f"Expected fact accuracy  {baseline_fact}/12"
        f"          {zero_fact}/12"
    )

    print("\nQuestions where overlap 10 passed but overlap 0 failed:")

    merged = baseline.merge(
        zero,
        on="question",
        suffixes=("_overlap10", "_overlap0")
    )

    found = False

    for _, row in merged.iterrows():
        if (
            row["expected_doc_overlap10"] != "NONE"
            and bool(row["fact_correct_overlap10"])
            and not bool(row["fact_correct_overlap0"])
        ):
            found = True
            print("-", row["question"])
            print("  Expected fact:", row["expected_fact_overlap0"])
            print("  Overlap 10:", row["answer_overlap10"])
            print("  Overlap 0:", row["answer_overlap0"])

    if not found:
        print("No such question found in this comparison.")

    print("\nComparison complete.")


if __name__ == "__main__":
    zero_results = evaluate_zero_overlap()
    compare_results(zero_results)
