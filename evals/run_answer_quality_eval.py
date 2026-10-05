"""答案质量评测：验证「生成层前提校验」是否真的生效。

为什么需要它：项目原有的 run_rag_eval.py 只看**检索结果**，
看不出"模型有没有被用户的错误前提带跑"。这一层评测补的是**答案质量**。

⚠️ 本脚本会【真实调用 DeepSeek API】，每条用例花 token。
   建议先只留 3 条试水，跑通后再放全量。

用法（在哪个目录下运行都可以）：

    export HF_ENDPOINT=https://hf-mirror.com
    ./.venv/Scripts/python.exe evals/run_answer_quality_eval.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(ROOT_DIR)  # retriever 用相对路径 data/chroma，必须切到项目根

from agents import Runner  # noqa: E402
from supportpilot.agent import create_support_agent  # noqa: E402

from eval_logging import log_eval_failure  # noqa: E402

CASES_PATH = ROOT_DIR / "evals" / "answer_cases.jsonl"


def load_cases() -> list[dict]:
    if not CASES_PATH.exists():
        print(f"[error] 找不到用例文件：{CASES_PATH}")
        sys.exit(1)
    return [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def check_assertions(case: dict, answer: str) -> dict:
    """三类断言：
        must_contain      —— 全部都要出现
        must_contain_any  —— 至少出现一个
        must_not_contain  —— 一个都不能出现
    """
    missing = [k for k in case.get("must_contain", []) if k not in answer]

    any_group = case.get("must_contain_any", [])
    any_failed = bool(any_group) and not any(k in answer for k in any_group)

    forbidden = [k for k in case.get("must_not_contain", []) if k in answer]

    return {
        "missing": missing,
        "any_failed": any_failed,
        "any_group": any_group,
        "forbidden": forbidden,
        "passed": not missing and not any_failed and not forbidden,
    }


async def evaluate_case(agent, case: dict) -> dict:
    query = case["query"]

    # 每条用例独立跑，不共用 conversation —— 避免上一条污染下一条
    result = await Runner.run(agent, query)
    answer = result.final_output or ""

    check = check_assertions(case, answer)

    if not check["passed"]:
        log_eval_failure(
            suite="answer_quality",
            case=query,
            expected={
                "must_contain": case.get("must_contain"),
                "must_contain_any": case.get("must_contain_any"),
                "must_not_contain": case.get("must_not_contain"),
            },
            actual=answer,
            details={
                "missing": check["missing"],
                "any_failed": check["any_failed"],
                "forbidden": check["forbidden"],
            },
        )

    return {"query": query, "tier": case.get("tier", ""), "answer": answer, **check}


async def main() -> None:
    cases = load_cases()
    agent = create_support_agent()

    print("=" * 60)
    print("Answer Quality Eval")
    print("=" * 60)

    results = []
    for case in cases:
        print()
        print("-" * 60)
        print(f"Query: {case['query']}")
        print(f"Tier : {case.get('tier', '')}")

        try:
            record = await evaluate_case(agent, case)
        except Exception as exc:
            print(f"调用失败：{exc}")
            results.append(
                {
                    "query": case["query"],
                    "tier": case.get("tier", ""),
                    "passed": False,
                    "missing": [],
                    "any_failed": False,
                    "any_group": [],
                    "forbidden": [],
                    "answer": f"<异常：{exc}>",
                }
            )
            continue

        results.append(record)

        print(f"Status: {'PASS' if record['passed'] else 'FAIL'}")
        if record["missing"]:
            print(f"   缺少关键词   : {record['missing']}")
        if record["any_failed"]:
            print(f"   缺少任一关键词: {record['any_group']}")
        if record["forbidden"]:
            print(f"   出现禁用词   : {record['forbidden']}")
        print(f"Answer: {record['answer']}")

    passed = sum(1 for r in results if r["passed"])

    print()
    print("=" * 60)
    print("Answer Quality Eval Summary")
    print("=" * 60)
    print(f"Pass Rate: {passed}/{len(results)} = {passed / len(results):.2%}")

    by_tier: dict[str, list[bool]] = {}
    for record in results:
        by_tier.setdefault(record["tier"], []).append(record["passed"])

    print()
    print("按 tier 拆分：")
    for tier, flags in sorted(by_tier.items()):
        print(f"   {tier:<20} {sum(flags)}/{len(flags)}")

    print()
    print("⚠️ 关键词断言很粗糙，必须配合人工抽查（读一遍每条 Answer）。")


if __name__ == "__main__":
    asyncio.run(main())
