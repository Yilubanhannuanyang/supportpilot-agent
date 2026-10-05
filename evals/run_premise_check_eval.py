"""OPT-006 前提校验的端到端评测。

与 tests/test_fact_check.py 的分工：
    · 单测     -> 纯函数、零成本，验证抽取逻辑本身
    · 本脚本   -> 真实调用 Agent，验证整条链路上"用户数字 -> 检索原文 -> 判定"是否正确

⚠️ 本脚本会真实调用 DeepSeek API，每条问题花 token。

用法（在哪个目录下运行都可以）：
    export HF_ENDPOINT=https://hf-mirror.com
    ./.venv/Scripts/python.exe evals/run_premise_check_eval.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(ROOT_DIR)  # 检索工具使用相对路径 data/chroma

from agents import Runner  # noqa: E402

from supportpilot.agent import create_support_agent  # noqa: E402
from supportpilot.observability.tracer import (  # noqa: E402
    new_trace_id,
    set_current_trace_id,
)
from supportpilot.verification.fact_check import (  # noqa: E402
    FactCheckResult,
    NumberMention,
    collect_kb_text,
    find_unverified_numbers,
    log_premise_conflict,
)

LOG_PATH = ROOT_DIR / "data" / "logs" / "premise_conflict.jsonl"

# 对照组：包含"该报"和"不该报"两种预期
CONTROLS: list[tuple[str, list[str]]] = [
    ("我听说你们退款要30天是真的吗", ["30"]),  # 错误前提，应检出
    ("退款多久到账？", []),  # 正常问题，不应检出
    ("签收8天还能无理由退货吗？", ["8"]),  # 政策边界，应检出
    ("你们公司CEO是谁？", []),  # 知识库无依据，应静默
]

# 反向验证组：全部是正常政策问题，一条都不应该被标记。
#
# ⚠️ 不要把「签收8天还能无理由退货吗？」之类**政策边界问题**放进这一组：
#    政策原文只写了 7 天和 15 天，用户说的 8 天确实找不到依据，
#    被标记是**正确行为**（该用例属于上面的对照组）。
#    早期版本把它重复放进两组，导致"误报"被虚计成 1/12。
NEGATIVES: list[str] = [
    "退款多久到账？",
    "订单多久发货？",
    "黑金会员有什么权益？",
    "退货的运费谁来出？",
    "付款后一般几天发出？",
    "超过7天还能无理由退货吗？",
    "定制商品支持7天无理由退货吗？",
    "商品有质量问题，15天内可以退货吗？",
    "订单超过72小时没发货怎么办？",
    "会员权益可以转让吗？",
]


async def ask(agent, query: str) -> str:
    """跑一轮单轮问答，返回知识库原文（用于判定）。"""
    result = await Runner.run(agent, query)
    return collect_kb_text(result)


async def main() -> None:
    agent = create_support_agent()

    lines_before = (
        len(LOG_PATH.read_text(encoding="utf-8").splitlines())
        if LOG_PATH.exists()
        else 0
    )

    print("=" * 70)
    print("OPT-006 前提校验 · 端到端评测")
    print("=" * 70)

    detected = 0
    detect_total = 0
    false_positive = 0
    control_total = 0

    print()
    print("【对照组：预期检出与预期静默】")
    print()
    for query, expected in CONTROLS:
        set_current_trace_id(new_trace_id())
        try:
            kb_text = await ask(agent, query)
        except Exception as exc:
            print(f"  {query:<30} 调用失败：{exc}")
            continue

        actual = find_unverified_numbers(query, kb_text)
        ok = actual == expected

        if expected:
            detect_total += 1
            detected += 1 if ok else 0
        else:
            control_total += 1
            false_positive += 1 if actual else 0

        print(
            "  %-28s 预期=%-8s 实际=%-8s %s"
            % (query, expected, actual, "PASS" if ok else "FAIL")
        )

    print()
    print("【反向验证组：全部是正常问题，一条都不该被标记】")
    print()
    for query in NEGATIVES:
        set_current_trace_id(new_trace_id())
        try:
            kb_text = await ask(agent, query)
        except Exception as exc:
            print(f"  {query:<30} 调用失败：{exc}")
            continue

        actual = find_unverified_numbers(query, kb_text)
        control_total += 1
        if actual:
            false_positive += 1
        print(
            "  %-28s 实际=%-8s %s"
            % (query, actual, "OK" if not actual else "误报")
        )

    lines_after = (
        len(LOG_PATH.read_text(encoding="utf-8").splitlines())
        if LOG_PATH.exists()
        else 0
    )

    print()
    print("=" * 70)
    print("OPT-006 Eval Summary")
    print("=" * 70)
    print(f"检出准确率       : {detected}/{detect_total}")
    print(f"误报             : {false_positive}/{control_total}（越接近 0 越好）")
    print()
    print("说明：本脚本只验证判定逻辑（find_unverified_numbers），")
    print("      不经过 run.py 的挂钩，因此上面的日志行数增量应为 0。")
    print(f"      日志实际行数：{lines_after - lines_before} -> {lines_after} 行")
    print()

    # 单独自检日志写入路径：直接调用 log_premise_conflict，确认文件会增长。
    synthetic = FactCheckResult(
        mentions=[NumberMention(raw="30 天", value="30", unit="天")],
        unverified=["30"],
        kb_sources=["refund_policy.txt"],
        kb_numbers=["1", "2", "3"],
    )
    log_premise_conflict(
        query="[self-check] 我听说你们退款要30天是真的吗",
        result=synthetic,
        answer_before="before",
        answer_after="after",
        mode="self_check",
    )
    lines_final = len(LOG_PATH.read_text(encoding="utf-8").splitlines())

    log_ok = lines_final == lines_after + 1
    print(f"日志写入自检     : {'PASS' if log_ok else 'FAIL'}（{lines_after} -> {lines_final}）")
    print()
    print("判据：检出 2/2 且 误报 0/12 且 日志自检 PASS 视为通过。")


if __name__ == "__main__":
    asyncio.run(main())
