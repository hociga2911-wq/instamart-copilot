
"""Part D: Offline RAG policy retrieval and evaluation."""

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = PROJECT_ROOT / "data" / "policies"
EVAL_FILE = PROJECT_ROOT / "data" / "raw" / "policy_eval.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

sys.path.insert(0, str(PROJECT_ROOT))
import mock_llm


CHUNK_SIZE = 40
CHUNK_OVERLAP = 10
TOP_K = 3

SYSTEM_PROMPT = """You are a POLICY ASSISTANT.

Answer the user's question using ONLY the information in the supplied policy context.
Do not use outside knowledge or make up policy details.
If the answer is not available in the context, respond exactly:
I could not find that information in the policy documents.

Keep the answer concise and factual."""


def load_policy_documents():
    """Load all .txt policy documents."""
    documents = {}

    for path in sorted(POLICY_DIR.glob("*.txt")):
        documents[path.name] = path.read_text(encoding="utf-8")

    if not documents:
        raise FileNotFoundError(
            f"No policy documents found in {POLICY_DIR}"
        )

    return documents


def split_into_chunks(text, chunk_size=CHUNK_SIZE,
                      overlap=CHUNK_OVERLAP):
    """Split text into overlapping word chunks.

    A final fragment containing 10 words or fewer is discarded.
    """
    words = text.split()
    chunks = []
    start = 0
    step = chunk_size - overlap

    while start < len(words):
        chunk_words = words[start:start + chunk_size]

        if len(chunk_words) > overlap:
            chunks.append(" ".join(chunk_words))

        if start + chunk_size >= len(words):
            break

        start += step

    return chunks


def build_policy_index():
    """Create policy chunks and fit a TF-IDF vectorizer."""
    documents = load_policy_documents()
    chunks = []

    for filename, text in documents.items():
        for chunk_number, chunk_text in enumerate(
            split_into_chunks(text), start=1
        ):
            chunks.append({
                "source": filename,
                "chunk_id": chunk_number,
                "text": chunk_text
            })

    if not chunks:
        raise ValueError("No policy chunks were created.")

    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(
        [chunk["text"] for chunk in chunks]
    )

    return chunks, vectorizer, matrix


# Build the index once when this module is imported.
CHUNKS, VECTORIZER, TFIDF_MATRIX = build_policy_index()


def retrieve(query, k=TOP_K):
    """Return the top-k chunks ranked by cosine similarity."""
    if not query or not query.strip():
        return []

    query_vector = VECTORIZER.transform([query])
    scores = cosine_similarity(
        query_vector, TFIDF_MATRIX
    ).flatten()

    ranked_indices = scores.argsort()[::-1][:k]

    results = []

    for index in ranked_indices:
        results.append({
            **CHUNKS[index],
            "score": float(scores[index])
        })

    return results


def answer(question):
    """Answer a question using retrieved policy context.

    Returns:
        (answer_text, sources)
    """
    retrieved = retrieve(question, k=TOP_K)

    if not retrieved:
        return (
            "I could not find that information in the policy documents.",
            []
        )

    context_parts = []

    for item in retrieved:
        context_parts.append(
            f"[{item['source']}] {item['text']}"
        )

    context = "\n".join(context_parts)

    user_prompt = (
        f"CONTEXT:\n{context}\n"
        f"QUESTION:\n{question}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response = mock_llm.chat(messages)
    answer_text = response.choices[0].message.content

    sources = list(dict.fromkeys(
        item["source"] for item in retrieved
    ))

    return answer_text, sources


def evaluate():
    """Evaluate document retrieval and answer accuracy."""
    evaluation = pd.read_csv(EVAL_FILE).fillna("")

    results = []

    for _, row in evaluation.iterrows():
        question = str(row["question"])
        expected_doc = str(row["expected_doc"])
        expected_fact = str(row["expected_fact"])

        answer_text, sources = answer(question)

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

    output_path = OUTPUT_DIR / "rag_evaluation.csv"
    results_df.to_csv(output_path, index=False)

    answerable = results_df[
        results_df["expected_doc"] != "NONE"
    ]

    unanswerable = results_df[
        results_df["expected_doc"] == "NONE"
    ]

    print("\n========== RAG EVALUATION ==========")

    print(f"Total questions: {len(results_df)}")
    print(f"Answerable questions: {len(answerable)}")
    print(f"Unanswerable questions: {len(unanswerable)}")

    print(
        "\nDocument retrieval:",
        f"{answerable['document_correct'].sum()}/"
        f"{len(answerable)}"
    )

    print(
        "Expected fact accuracy:",
        f"{answerable['fact_correct'].sum()}/"
        f"{len(answerable)}"
    )

    print(
        "Correct fallback responses:",
        f"{unanswerable['fallback_correct'].sum()}/"
        f"{len(unanswerable)}"
    )

    print("\nChunk distribution:")

    distribution = pd.Series(
        [chunk["source"] for chunk in CHUNKS]
    ).value_counts().sort_index()

    print(distribution.to_string())
    print(f"\nTotal chunks: {len(CHUNKS)}")

    print("\nQuestions with incorrect expected facts:")

    failed = answerable[
    answerable["fact_correct"].map(lambda value: not value)
]

    if failed.empty:
        print("None")
    else:
        for _, row in failed.iterrows():
            print("-", row["question"])
            print("  Answer:", row["answer"])

    print("\nSaved evaluation:", output_path)

    return results_df


if __name__ == "__main__":
    print("Policy chunks:", len(CHUNKS))

    print("\nChunk distribution:")
    for filename in sorted({
        chunk["source"] for chunk in CHUNKS
    }):
        count = sum(
            chunk["source"] == filename for chunk in CHUNKS
        )
        print(f"{filename}: {count}")

    print("\nTop 3 results for test query:")
    test_query = "refund policy late delivery"

    for result in retrieve(test_query, k=3):
        print(
            f"{result['source']} | "
            f"score={result['score']:.4f}"
        )

    evaluate()
