"""按 trace_id 还原一次会话的完整链路。

把三个互不关联的日志文件（RAG 检索 / Workflow 轨迹 / 人工审批）
里属于同一个 trace_id 的记录，按时间顺序合并打印出来。

用法（在哪个目录下运行都可以）：

    # 查看某个链路
    ./.venv/Scripts/python.exe src/supportpilot/observability/show_trace.py tr-9f3a1c2b

    # 不带参数：列出最近 10 个 trace_id，方便挑选
    ./.venv/Scripts/python.exe src/supportpilot/observability/show_trace.py
"""

import json
import sys
import unicodedata
from pathlib import Path

# src/supportpilot/observability/show_trace.py
#   parents[0]=observability  [1]=supportpilot  [2]=src  [3]=项目根
ROOT_DIR = Path(__file__).resolve().parents[3]

LOG_DIR = ROOT_DIR / "data" / "logs"

# (来源标记, 文件路径)
LOG_FILES = [
    ("rag", LOG_DIR / "rag_retrieval.jsonl"),
    ("workflow", LOG_DIR / "workflow_trace.jsonl"),
    ("approval", LOG_DIR / "approval_log.jsonl"),
    ("premise", LOG_DIR / "premise_conflict.jsonl"),
]

SOURCE_LABEL = {
    "rag": "RAG 检索",
    "workflow": "Workflow 轨迹",
    "approval": "人工审批",
    "premise": "前提校验",
}

RECENT_LIMIT = 10


def disp_width(text: str) -> int:
    """中文字符占 2 列，英文占 1 列，用于终端对齐。"""
    return sum(
        2 if unicodedata.east_asian_width(c) in "WF" else 1
        for c in str(text)
    )


def pad(text: str, width: int) -> str:
    text = str(text)
    return text + " " * max(0, width - disp_width(text))


def read_records() -> list[dict]:
    """读取三个日志，给每条记录补上 _source 标记。

    ⚠️ 用 .get("trace_id") 而不是 ["trace_id"]：
       加 trace_id 之前写下的旧日志没有这个字段，直接取会 KeyError。
    """
    records = []

    for source, path in LOG_FILES:
        if not path.exists():
            continue

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # 跳过写坏的半行

            record["_source"] = source
            records.append(record)

    return records


def list_recent_trace_ids(records: list[dict]) -> list[str]:
    """按时间倒序取出最近出现过的 trace_id。"""
    seen: list[str] = []

    for record in sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True):
        trace_id = record.get("trace_id")
        if trace_id and trace_id not in seen:
            seen.append(trace_id)
        if len(seen) >= RECENT_LIMIT:
            break

    return seen


def format_record(record: dict) -> str:
    """按来源把记录压成一行可读文本。"""
    source = record["_source"]

    if source == "rag":
        return "查询=%s  来源=%s  距离=%s  通过=%s" % (
            record.get("query"),
            record.get("source"),
            record.get("distance"),
            record.get("passed"),
        )

    if source == "workflow":
        return "订单=%s  步骤=%s  超时=%s  工单=%s  复用=%s" % (
            record.get("order_id"),
            record.get("current_step"),
            record.get("is_overdue"),
            record.get("ticket_id"),
            record.get("ticket_reused"),
        )

    if source == "premise":
        return "提问=%s  存疑数值=%s  依据=%s  模式=%s" % (
            record.get("query"),
            record.get("unverified_numbers"),
            record.get("kb_sources"),
            record.get("mode"),
        )

    return "动作=%s  对象=%s  决定=%s  成功=%s  %s" % (
        record.get("action"),
        record.get("target_id"),
        record.get("decision"),
        record.get("success"),
        record.get("message", ""),
    )


def main() -> None:
    records = read_records()

    if not records:
        print(f"日志目录里没有可读记录：{LOG_DIR}")
        print("提示：先跑一轮 run.py 产生日志。")
        return

    if len(sys.argv) < 2:
        print("=" * 78)
        print("用法：show_trace.py <trace_id>")
        print("=" * 78)
        print()
        print("最近的 trace_id：")
        print()
        for trace_id in list_recent_trace_ids(records):
            print("   ", trace_id)
        print()
        print("挑一个再跑：show_trace.py <trace_id>")
        return

    target = sys.argv[1].strip()
    matched = [r for r in records if r.get("trace_id") == target]

    print("=" * 78)
    print(f"链路还原：{target}")
    print("=" * 78)
    print()

    if not matched:
        print("没有找到属于这个 trace_id 的记录。")
        print("可能原因：① ID 拼写有误；② 该记录写在加 trace_id 之前。")
        return

    matched.sort(key=lambda r: r.get("timestamp", ""))

    for index, record in enumerate(matched, start=1):
        timestamp = str(record.get("timestamp", ""))[:19]
        label = SOURCE_LABEL.get(record["_source"], record["_source"])
        print("%2d. %s  %s" % (index, timestamp, pad(label, 14)))
        print("      " + format_record(record))

    print()
    counts = {}
    for record in matched:
        counts[record["_source"]] = counts.get(record["_source"], 0) + 1
    print(
        "合计 %d 条：%s"
        % (
            len(matched),
            "  ".join(f"{k}={v}" for k, v in counts.items()),
        )
    )
    print("DONE")


if __name__ == "__main__":
    main()
