"""查题小工具：先看某条问题实际命中哪个文档，再决定 expected_source。

为什么需要它：标注 expected_source 时如果"凭感觉填"，很容易把域内题标成域外
（这个坑踩过一次，直接把"分离空隙"从真实的 0.1252 变成了假象的 0.0059）。
所以规则是——**先实测，再标注**。

只读脚本：只在内存里把 MAX_DISTANCE 关掉，不改动任何项目文件。

用法（在哪个目录下运行都可以）：

    1) 直接把问题写在命令行后面：
       ./.venv/Scripts/python.exe evals/inspect_query.py "退货" "多久到"

    2) 中文参数在命令行里乱码时，改用文件（一行一条，UTF-8）：
       ./.venv/Scripts/python.exe evals/inspect_query.py --file queries.txt
"""

import contextlib
import io
import os
import sys
import unicodedata
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(ROOT_DIR)

import supportpilot.rag.retriever as R  # noqa: E402  必须在 sys.path 之后导入

DEFAULT_TOP_K = 3


def disp_width(text: str) -> int:
    """中文字符占 2 列，英文占 1 列，用于终端表格对齐。"""
    return sum(
        2 if unicodedata.east_asian_width(c) in "WF" else 1
        for c in str(text)
    )


def pad(text: str, width: int) -> str:
    text = str(text)
    return text + " " * max(0, width - disp_width(text))


def load_queries(argv: list[str]) -> list[str]:
    """支持两种入口：--file <路径> 或 直接跟在命令后面的问题。"""
    if argv and argv[0] == "--file":
        if len(argv) < 2:
            print("[error] --file 后面要跟文件路径")
            sys.exit(1)
        path = Path(argv[1])
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.exists():
            print(f"[error] 找不到文件：{path}")
            sys.exit(1)
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return [q for q in argv if q.strip()]


def main() -> None:
    queries = load_queries(sys.argv[1:])

    if not queries:
        print(__doc__)
        sys.exit(0)

    # 关掉阈值过滤，避免"被阈值拦掉"掩盖了真实的 top1
    R.MAX_DISTANCE = 99.0

    print("=" * 78)
    print("查题工具：看每条问题实际命中的 top1 文档（已关闭阈值过滤）")
    print("=" * 78)
    print()

    width = max([disp_width(q) for q in queries] + [20])
    print("  " + pad("提问", width) + "  " + pad("top1 来源", 24) + "距离")
    print("  " + "-" * (width + 34))

    for query in queries:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            results = R.search_knowledge_base(query, top_k=DEFAULT_TOP_K)

        top1 = results[0] if results else None
        print(
            "  "
            + pad(query, width)
            + "  "
            + pad(top1["source"] if top1 else "（无结果）", 24)
            + ("%.4f" % top1["distance"] if top1 else "—")
        )

    print()
    print("提醒：把上面实测到的 top1 来源写进 expected_source，不要凭感觉填。")
    print("DONE")


if __name__ == "__main__":
    main()
