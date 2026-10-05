import json
import sys
from pathlib import Path
from eval_logging import log_eval_failure

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

sys.path.insert(
    0,
    str(SRC_DIR),
)


from supportpilot.rag.retriever import search_knowledge_base


CASES_PATH = ROOT_DIR / "evals" / "rag_cases_hard.jsonl"


MIN_TOP1_ACCURACY = 1.0
MIN_RECALL_AT_3 = 1.0
MIN_NO_ANSWER_ACCURACY = 1.0


def load_cases() -> list[dict]:
    cases = []

    with CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            cases.append(
                json.loads(line)
            )

    return cases


def run_eval() -> None:
    cases = load_cases()

    top1_correct = 0
    recall_at_3_correct = 0
    positive_total = 0

    no_answer_correct = 0
    no_answer_total = 0

    print("=" * 50)
    print("RAG Eval (Hard)")
    print("=" * 50)

    for case in cases:
        query = case["query"]
        expected_source = case["expected_source"]

        results = search_knowledge_base(
            query=query,
            top_k=3,
        )

        top1_source = (
            results[0]["source"]
            if results
            else None
        )

        top3_sources = [
            item["source"]
            for item in results
        ]

        print()
        print("-" * 50)
        print(f"Query: {query}")
        print(f"Expected: {expected_source}")
        print(f"Top1: {top1_source}")
        print(f"Top3: {top3_sources}")

        if expected_source is None:
            no_answer_total += 1

            passed = top1_source is None

            if not passed:
                log_eval_failure(
                    suite="rag_hard_no_answer",
                    case=query,
                    expected={
                    "top1": None,
                },
                actual={
                    "top1": top1_source,
                    "top3": top3_sources,
                },
        )

            if passed:
                no_answer_correct += 1

            print(
                f"No-answer: "
                f"{'PASS' if passed else 'FAIL'}"
            )

            continue

        positive_total += 1

        top1_passed = (
            top1_source
            == expected_source
        )

        recall_passed = (
            expected_source
            in top3_sources
        )

        if not top1_passed or not recall_passed:
            log_eval_failure(
                suite="rag_hard",
                case=query,
            expected={
                "source": expected_source,
        },
            actual={
                "top1": top1_source,
                "top3": top3_sources,
        },
            details={
                "top1_passed": top1_passed,
                "recall_at_3_passed": recall_passed,
        },
    )

        if top1_passed:
            top1_correct += 1

        if recall_passed:
            recall_at_3_correct += 1

        print(
            f"Top1: "
            f"{'PASS' if top1_passed else 'FAIL'}"
        )

        print(
            f"Recall@3: "
            f"{'PASS' if recall_passed else 'FAIL'}"
        )

    top1_accuracy = (
        top1_correct / positive_total
        if positive_total
        else 0
    )

    recall_at_3 = (
        recall_at_3_correct / positive_total
        if positive_total
        else 0
    )

    no_answer_accuracy = (
        no_answer_correct / no_answer_total
        if no_answer_total
        else 0
    )

    print()
    print("=" * 50)
    print("RAG Eval Summary")
    print("=" * 50)

    print(
        f"Top1 Accuracy: "
        f"{top1_correct}/{positive_total} "
        f"= {top1_accuracy:.2%}"
    )

    print(
        f"Recall@3: "
        f"{recall_at_3_correct}/{positive_total} "
        f"= {recall_at_3:.2%}"
    )

    print(
        f"No-answer Accuracy: "
        f"{no_answer_correct}/{no_answer_total} "
        f"= {no_answer_accuracy:.2%}"
    )

    quality_gate_passed = (
        top1_accuracy >= MIN_TOP1_ACCURACY
        and recall_at_3 >= MIN_RECALL_AT_3
        and no_answer_accuracy >= MIN_NO_ANSWER_ACCURACY
    )

    print()
    print("=" * 50)
    print("RAG Quality Gate")
    print("=" * 50)

    if quality_gate_passed:
        print("Status: PASS")
    else:
        print("Status: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    run_eval()