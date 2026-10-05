"""从 prompts/*.yaml 加载 Agent 的 Prompt 场景包。

设计要点：
1. 用【绝对路径】定位 prompts/ 目录（parents[2] = 项目根），
   避免"必须在项目根目录运行"这个坑。
2. 用 yaml.safe_load 而不是 yaml.load —— 后者能反序列化任意 Python 对象，有安全风险。
3. 用 "".join() 而不是 "\\n".join() —— 原 instructions 是相邻字符串字面量隐式拼接，
   字与字之间没有任何分隔符；用换行拼接会改变 prompt 内容。
"""

from pathlib import Path

import yaml

# src/supportpilot/prompt_loader.py
#   parents[0] = supportpilot
#   parents[1] = src
#   parents[2] = 项目根
PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"

DEFAULT_SCENARIO = "support_agent"


def load_prompt_blocks(name: str = DEFAULT_SCENARIO) -> list[dict]:
    """读取场景包，返回 block 列表。"""
    path = PROMPT_DIR / f"{name}.yaml"

    if not path.exists():
        raise FileNotFoundError(f"Prompt 场景包不存在：{path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    blocks = data.get("blocks") or []
    if not blocks:
        raise ValueError(f"Prompt 场景包没有 blocks：{path}")

    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict) or "text" not in block:
            raise ValueError(f"第 {index} 个 block 缺少 text 字段：{path}")

    return blocks


def load_instructions(name: str = DEFAULT_SCENARIO) -> str:
    """按 blocks 顺序拼接出完整的 instructions 字符串。"""
    return "".join(block["text"] for block in load_prompt_blocks(name))
