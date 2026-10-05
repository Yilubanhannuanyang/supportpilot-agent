"""阈值扫描实验：观察 MAX_DISTANCE 变化如何影响 Top1 / Recall@3 / 拒答准确率。

把 MAX_DISTANCE 从 0.40 到 0.70 逐个跑一遍：
  · 官方评测集 evals/rag_cases.jsonl（5 条）—— 决定 Quality Gate 是否 PASS
  · 扩展集   evals/rag_cases_hard.jsonl（25 条）—— 看阈值收放的真实代价

只读脚本：只在内存里改 MAX_DISTANCE，不改动任何项目文件。

用法（在哪个目录下运行都可以）：
    ./.venv/Scripts/python.exe evals/threshold_sweep.py
"""

import contextlib
import io
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(ROOT_DIR)

import supportpilot.rag.retriever as R  # noqa: E402  必须在 sys.path 之后导入

OFFICIAL_PATH = ROOT_DIR / "evals" / "rag_cases.jsonl"
HARD_PATH = ROOT_DIR / "evals" / "rag_cases_hard.jsonl"

THRESHOLDS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.70]


def load_cases(path: Path) -> list[dict]:
    if not path.exists():
        print(f"[warn] 找不到用例文件：{path}")
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieve_quiet(query: str, top_k: int = 3) -> list[dict]:
    """调用检索，但屏蔽 retriever 自己的 print，避免刷屏。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return R.search_knowledge_base(query, top_k=top_k)


def eval_official(cases: list[dict]) -> dict:
    top1_correct = 0
    recall_correct = 0
    positive_total = 0
    no_answer_correct = 0
    no_answer_total = 0

    for case in cases:
        results = retrieve_quiet(case["query"])
        top1_source = results[0]["source"] if results else None
        top3_sources = [r["source"] for r in results]
        expected = case["expected_source"]

        if expected is None:
            no_answer_total += 1
            if top1_source is None:
                no_answer_correct += 1
            continue

        positive_total += 1
        if top1_source == expected:
            top1_correct += 1
        if expected in top3_sources:
            recall_correct += 1

    return {
        "top1": top1_correct,
        "recall": recall_correct,
        "positive": positive_total,
        "no_answer": no_answer_correct,
        "no_answer_total": no_answer_total,
    }


def eval_hard(cases: list[dict]) -> dict:
    ok_in = 0
    total_in = 0
    leaked = 0
    total_out = 0

    for case in cases:
        results = retrieve_quiet(case["query"])
        expected = case["expected_source"]

        if expected is None:
            total_out += 1
            if results:
                leaked += 1
            continue

        total_in += 1
        if results and results[0]["source"] == expected:
            ok_in += 1

    return {"ok_in": ok_in, "total_in": total_in, "leaked": leaked, "total_out": total_out}


def pct(numerator: int, denominator: int) -> str:
    if not denominator:
        return "  n/a"
    return "%d/%d = %5.1f%%" % (numerator, denominator, 100.0 * numerator / denominator)


def main() -> None:
    official_cases = load_cases(OFFICIAL_PATH)
    hard_cases = load_cases(HARD_PATH)
    original = R.MAX_DISTANCE

    print("=" * 78)
    print("MAX_DISTANCE 阈值扫描：改这个参数到底影响什么")
    print("=" * 78)
    print()

    rows = []
    for th in THRESHOLDS:
        R.MAX_DISTANCE = th
        rows.append((th, eval_official(official_cases), eval_hard(hard_cases)))

    print("【官方评测集 %d 条 —— 决定 Quality Gate 是否 PASS】" % len(official_cases))
    print()
    print("  阈值      Top1 准确率        Recall@3           拒答准确率(no-answer)")
    print("  " + "-" * 70)
    for th, off, _ in rows:
        print(
            "  %-8.2f %-18s %-18s %s"
            % (
                th,
                pct(off["top1"], off["positive"]),
                pct(off["recall"], off["positive"]),
                pct(off["no_answer"], off["no_answer_total"]),
            )
        )

    print()
    print("【扩展集 %d 条 —— 看阈值收紧/放宽的真实代价】" % len(hard_cases))
    print()
    print("  阈值      域内命中          域外漏过")
    print("  " + "-" * 46)
    for th, _, hard in rows:
        print(
            "  %-8.2f %-18s %s"
            % (
                th,
                "%d/%d" % (hard["ok_in"], hard["total_in"]),
                "%d/%d" % (hard["leaked"], hard["total_out"]),
            )
        )

    print()
    print("=" * 78)
    print("解读要点")
    print("=" * 78)
    print("  · Top1 / Recall@3 只在【正样本】上计算（expected_source 不为 null 的用例）")
    print("  · 拒答准确率只在【拒答用例】上算，且判定极严：必须一条都检索不到才算过")
    print("  · 阈值收紧 -> 拒答变好，但 Top1 / Recall@3 有下降风险（把真问题也拦掉了）")
    print("  · 阈值放宽 -> Top1 / Recall@3 稳，但拒答失效（模型拿到不相关资料去编答案）")
    print()
    print("  注意：官方集对 MAX_DISTANCE 往往不敏感（各阈值下数字一动不动），")
    print("        真正能看出差异的是扩展集。详见 SupportPilot_RAG阈值标定实验报告.md")
    print()
    print("项目原始 MAX_DISTANCE = %.2f" % original)
    print("DONE")


if __name__ == "__main__":
    main()
