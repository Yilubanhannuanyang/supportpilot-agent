"""阈值标定探针：量化 MAX_DISTANCE 的实际拦截效果。

思路：把 MAX_DISTANCE 临时调到 99 关掉过滤，拿到扩展集（域内 9 条 + 域外 9 条）
每条问题的原始 top1 距离，再对多个候选阈值统计"域外漏过多少条 / 域内误杀多少条"。

只读脚本：只在内存里改 MAX_DISTANCE，不改动任何项目文件。
原始距离另存一份 JSON（data/logs/threshold_probe.json），方便回填实验报告。

用法（在哪个目录下运行都可以）：
    ./.venv/Scripts/python.exe evals/probe_threshold.py
"""

import contextlib
import io
import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(ROOT_DIR)

import supportpilot.rag.retriever as R  # noqa: E402  必须在 sys.path 之后导入

# 只读扩展集（域内 9 条 + 域外 9 条）。
# 官方集那 5 条距离落在"怎么调阈值都命中/都拦得住"的两端，对阈值完全不敏感，
# 没必要求它们的原始距离；要看官方集在各阈值下的表现，跑 evals/threshold_sweep.py。
CASE_FILE = ROOT_DIR / "evals" / "rag_cases_hard.jsonl"

THRESHOLDS = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70]

OUT_JSON = ROOT_DIR / "data" / "logs" / "threshold_probe.json"


def disp_width(text: str) -> int:
    """中文字符占 2 列，英文字符占 1 列，用于终端表格对齐。"""
    return sum(
        2 if unicodedata.east_asian_width(c) in "WF" else 1
        for c in str(text)
    )


def pad(text: str, width: int) -> str:
    text = str(text)
    return text + " " * max(0, width - disp_width(text))


def load_cases() -> list[dict]:
    if not CASE_FILE.exists():
        print(f"[error] 找不到用例文件：{CASE_FILE}")
        sys.exit(1)
    return [
        json.loads(line)
        for line in CASE_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieve_quiet(query: str, top_k: int = 3) -> list[dict]:
    """调用检索，但屏蔽 retriever 自己的 print，避免刷屏。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return R.search_knowledge_base(query, top_k=top_k)


def main() -> None:
    project_max_distance = R.MAX_DISTANCE
    R.MAX_DISTANCE = 99.0

    cases = load_cases()

    in_rows = []
    out_rows = []

    for case in cases:
        query = case["query"]
        expected = case.get("expected_source")

        results = retrieve_quiet(query)
        top1 = results[0] if results else None

        if expected is None:
            out_rows.append(
                {
                    "query": query,
                    "distance": top1["distance"] if top1 else None,
                    "returned": len(results),
                    "tier": case.get("tier", ""),
                }
            )
        else:
            in_rows.append(
                {
                    "query": query,
                    "top1": top1["source"] if top1 else None,
                    "distance": top1["distance"] if top1 else None,
                    "hit": bool(top1) and top1["source"] == expected,
                    "expected": expected,
                }
            )

    q_width = max([disp_width(r["query"]) for r in in_rows + out_rows] + [20])

    print("=" * 78)
    print("一、域内问题（应该命中正确文档，距离越小越好）")
    print("=" * 78)
    for r in in_rows:
        if r["distance"] is None:
            print(pad(r["query"], q_width) + "  无结果")
            continue
        flag = "命中" if r["hit"] else "错命中 -> " + str(r["top1"])
        print(
            pad(r["query"], q_width)
            + "  top1=" + pad(r["top1"], 22)
            + " d=%.4f  %s" % (r["distance"], flag)
        )

    print()
    print("=" * 78)
    print("二、域外问题（知识库里没有，理想情况应全部拦掉）")
    print("=" * 78)
    for r in out_rows:
        if r["distance"] is None:
            print(pad(r["query"], q_width) + "  无结果（已拦掉）")
            continue
        print(
            pad(r["query"], q_width)
            + "  top1_d=%.4f  返回%d条  [%s]"
            % (r["distance"], r["returned"], r["tier"])
        )

    in_dists = [r["distance"] for r in in_rows if r["distance"] is not None]
    out_dists = [r["distance"] for r in out_rows if r["distance"] is not None]

    print()
    print("=" * 78)
    print("三、阈值标定表：不同 MAX_DISTANCE 下，域外漏过 / 域内误杀")
    print("=" * 78)
    print("  " + pad("候选阈值", 12) + pad("域外漏过", 14) + "域内误杀")
    print("  " + "-" * 40)

    calibration = []
    for th in THRESHOLDS:
        leaked = sum(1 for d in out_dists if d <= th)
        killed = sum(1 for d in in_dists if d > th)
        calibration.append({"threshold": th, "leaked": leaked, "killed": killed})
        mark = "  <-- 项目当前" if abs(th - project_max_distance) < 1e-9 else ""
        print(
            "  " + pad("%.2f" % th, 12)
            + pad("%d/%d" % (leaked, len(out_dists)), 14)
            + "%d/%d" % (killed, len(in_dists))
            + mark
        )

    print()
    if in_dists:
        print(
            "域内 top1 距离: min=%.4f  max=%.4f  mean=%.4f  (共 %d 条)"
            % (min(in_dists), max(in_dists), sum(in_dists) / len(in_dists), len(in_dists))
        )
    if out_dists:
        print(
            "域外 top1 距离: min=%.4f  max=%.4f  mean=%.4f  (共 %d 条)"
            % (min(out_dists), max(out_dists), sum(out_dists) / len(out_dists), len(out_dists))
        )
    print("项目当前 MAX_DISTANCE = %.2f" % project_max_distance)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_max_distance": project_max_distance,
        "case_file": str(CASE_FILE.relative_to(ROOT_DIR)),
        "in_domain": in_rows,
        "out_of_domain": out_rows,
        "calibration": calibration,
        "summary": {
            "in_domain_count": len(in_dists),
            "out_of_domain_count": len(out_dists),
            "in_domain_min": min(in_dists) if in_dists else None,
            "in_domain_max": max(in_dists) if in_dists else None,
            "out_of_domain_min": min(out_dists) if out_dists else None,
            "out_of_domain_max": max(out_dists) if out_dists else None,
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print()
    print("原始距离已保存：%s" % OUT_JSON.relative_to(ROOT_DIR))
    print("DONE")


if __name__ == "__main__":
    main()
