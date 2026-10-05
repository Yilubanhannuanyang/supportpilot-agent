r"""查看 SupportPilot 的数据库与日志。

用法（在项目根目录执行）：
    .\.venv\Scripts\python.exe show_db.py

这个脚本只读，不会修改任何数据。
"""

import json
import sqlite3
import unicodedata
from pathlib import Path

# 以脚本所在目录为基准，这样在任何目录下执行都能找到文件
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "supportpilot.db"
LOG_DIR = ROOT / "data" / "logs"


def disp_width(text):
    """计算字符串的显示宽度：中文/全角字符算 2，其余算 1。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(text))


def pad(text, width):
    """按显示宽度右侧补空格，保证中英文混排时列能对齐。"""
    text = str(text)
    return text + " " * max(0, width - disp_width(text))


def show_table(conn, table, title, note):
    print("=" * 68)
    print(title)
    print(note)
    print("=" * 68)

    cols = [r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)]
    if not cols:
        print("  表不存在")
        print()
        return 0

    rows = list(conn.execute("SELECT * FROM %s" % table))

    widths = []
    for i, c in enumerate(cols):
        widths.append(max([disp_width(c)] + [disp_width(r[i]) for r in rows]))

    header = "  " + "  ".join(pad(c, widths[i]) for i, c in enumerate(cols))
    print(header.rstrip())
    print("  " + "-" * (disp_width(header) - 2))

    for r in rows:
        print("  " + "  ".join(pad(r[i], widths[i]) for i in range(len(cols))).rstrip())

    print("  共 %d 条" % len(rows))
    print()
    return len(rows)


def show_log(filename, title, formatter):
    path = LOG_DIR / filename
    print("=" * 68)
    print(title)
    print("=" * 68)

    if not path.is_file():
        print("  文件不存在（还没产生记录）")
        print()
        return

    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("  共 %d 条记录" % len(lines))
    for i, line in enumerate(lines, 1):
        try:
            print("   [%d] %s" % (i, formatter(json.loads(line))))
        except Exception as e:
            print("   [%d] 解析失败：%s" % (i, e))
    print()


def main():
    if not DB_PATH.is_file():
        print("找不到数据库：%s" % DB_PATH)
        print()
        print("请先初始化数据库：")
        print(r'  .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,\'src\'); from supportpilot.db import init_db; init_db()"')
        return

    print()
    print("数据库文件：%s" % DB_PATH)
    print()

    conn = sqlite3.connect(DB_PATH)

    show_table(
        conn, "orders",
        "【订单表 orders】",
        "初始化种子数据，固定 4 条，任何审批都不会改动它",
    )

    n_tickets = show_table(
        conn, "tickets",
        "【工单表 tickets】",
        "★ approve 通过后才会出现记录；reject 则始终为 0 条",
    )

    conn.close()

    if n_tickets == 0:
        print(">>> 工单表为空，有两种含义：")
        print("    (1) 还没跑过建单流程；")
        print("    (2) 跑过但都点了 reject —— 这正是 HITL 安全闸门生效的证据。")
        print()

    show_log(
        "approval_log.jsonl",
        "【人工审批审计日志 approval_log.jsonl】",
        lambda r: "%-19s 动作=%-24s 对象=%-8s 决定=%-9s 成功=%s\n         %s" % (
            r.get("timestamp", "")[:19], r.get("action"), r.get("target_id"),
            r.get("decision"), r.get("success"), r.get("message", ""),
        ),
    )

    show_log(
        "workflow_trace.jsonl",
        "【工作流轨迹 workflow_trace.jsonl】",
        lambda r: "%-19s 订单=%-6s 终态=%-18s 超时=%-6s 工单=%-6s 复用=%s" % (
            r.get("timestamp", "")[:19], r.get("order_id"), r.get("current_step"),
            r.get("is_overdue"), r.get("ticket_id"), r.get("ticket_reused"),
        ),
    )


if __name__ == "__main__":
    main()
