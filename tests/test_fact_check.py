"""fact_check 的纯函数单测：不调用 LLM、不访问网络、零成本。

运行：
    ./.venv/Scripts/python.exe -m pytest tests/ -v
"""

from pathlib import Path

import pytest

from agents import Agent
from agents.items import ToolCallOutputItem

from supportpilot.verification.fact_check import (
    check_premise,
    collect_kb_text,
    extract_known_numbers,
    extract_user_numbers,
    find_unverified_numbers,
    parse_kb_chunks,
    should_regenerate,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT_DIR / "data" / "knowledge"

# 与 tools/kb_tools.py 的真实输出格式逐字符一致的合成串。
# ⚠️ 若 kb_tools.py 改了输出格式，这里必须同步改 —— 这就是格式耦合的护栏。
KB_REFUND = (
    "[资料 1]\n"
    "来源：refund_policy.txt\n"
    "内容：银行卡退款到账时间通常为 3 至 7 个工作日。"
)

KB_NOT_FOUND = "知识库中未找到相关内容。"


# ---------------------------------------------------------------------------
# 主入口：find_unverified_numbers
# ---------------------------------------------------------------------------


def test_wrong_premise_is_flagged():
    """用户说 30 天，原文写 3~7 个工作日 -> 标记 30。"""
    assert find_unverified_numbers("我听说你们退款要30天是真的吗", KB_REFUND) == ["30"]


def test_no_number_in_query_is_silent():
    """问题里没有数字 -> 不标记。"""
    assert find_unverified_numbers("退款多久到账？", KB_REFUND) == []


def test_boundary_case_is_flagged():
    """政策是 7 天无理由，用户问第 8 天 -> 标记 8。"""
    assert find_unverified_numbers("签收8天还能无理由退货吗？", KB_REFUND) == ["8"]


def test_order_id_is_not_extracted():
    """订单号 A1001 不含单位，必须被排除；只抽到 30。"""
    assert find_unverified_numbers("订单A1001退款要30天吗", KB_REFUND) == ["30"]


def test_kb_chunk_marker_is_not_treated_as_policy_number():
    """★ 本模块最重要的一条回归。

    kb_text 里的分块序号 "[资料 1]" 含数字 1，若实现时把整段 kb_text
    （而非 content）交给抽取器，1 会变成"已知数字"，导致用户说的 1 天
    不被标记。该断言专门用来抓这个 bug。
    """
    assert find_unverified_numbers("退款要1天吗", KB_REFUND) == ["1"]


def test_range_expansion_makes_inner_values_known():
    """区间 3~7 展开后，5 天属于"区间内"，按设计不标记（用召回换精度）。"""
    assert find_unverified_numbers("退款要5天吗", KB_REFUND) == []


def test_empty_kb_text_is_silent():
    """没有知识库依据时跳过，属"无保护"而非"误报"。"""
    assert find_unverified_numbers("退款要30天吗", "") == []
    assert find_unverified_numbers("退款要30天吗", "   ") == []


def test_kb_tool_not_found_output_is_silent():
    """知识库工具明确回"未找到"时，不应产生标记。"""
    assert find_unverified_numbers("退款要30天吗", KB_NOT_FOUND) == []


# ---------------------------------------------------------------------------
# 抽取函数
# ---------------------------------------------------------------------------


def test_user_numbers_handle_spaces_and_units():
    """数字与单位之间可能有空格，两侧都要容忍。"""
    values = {m.value for m in extract_user_numbers("退款要 30 天，超过 48 小时没发货")}
    assert values == {"30", "48"}


def test_user_numbers_ignore_ids_without_units():
    values = {m.value for m in extract_user_numbers("A1001 T0001 tr-9f3a1c2b")}
    assert values == set()


def test_known_numbers_strip_list_markers_and_expand_ranges():
    chunks = [{"source": "x.txt", "content": "1. 平台将在 3 至 7 个工作日内处理。\n2. 其他说明。"}]
    known = extract_known_numbers(chunks)
    # 列表序号 1、2 被剥掉；区间 3~7 被展开
    assert "1" not in known
    assert {"3", "4", "5", "6", "7"} <= known


def test_parse_kb_chunks_splits_multiple_chunks():
    text = (
        "[资料 1]\n来源：refund_policy.txt\n内容：甲\n\n"
        "[资料 2]\n来源：return_policy.txt\n内容：乙"
    )
    chunks = parse_kb_chunks(text)
    assert [c["source"] for c in chunks] == ["refund_policy.txt", "return_policy.txt"]


# ---------------------------------------------------------------------------
# 真实知识库数据（仍为零成本：只读磁盘文件）
# ---------------------------------------------------------------------------


def _real_kb_text() -> str:
    """把磁盘上的 4 份政策拼成知识库工具的完整输出格式。"""
    parts = []
    for index, path in enumerate(sorted(KNOWLEDGE_DIR.glob("*.txt")), start=1):
        parts.append(
            f"[资料 {index}]\n"
            f"来源：{path.name}\n"
            f"内容：{path.read_text(encoding='utf-8')}"
        )
    return "\n\n".join(parts)


@pytest.mark.skipif(not KNOWLEDGE_DIR.exists(), reason="知识库目录不存在")
def test_real_knowledge_base_numbers_are_known():
    """用真实政策原文验证：政策里出现过的数字不应被标记。"""
    kb = _real_kb_text()

    # 政策原文里确实存在的数字
    for query in ["退款要15天吗", "发货要48小时吗", "发货要72小时吗", "退货要7天吗"]:
        assert find_unverified_numbers(query, kb) == [], query


@pytest.mark.skipif(not KNOWLEDGE_DIR.exists(), reason="知识库目录不存在")
def test_real_knowledge_base_flags_unsupported_numbers():
    """政策里不存在的数字应当被标记。"""
    kb = _real_kb_text()
    assert find_unverified_numbers("我听说你们退款要30天是真的吗", kb) == ["30"]
    assert find_unverified_numbers("发货要24小时吗", kb) == ["24"]


# ---------------------------------------------------------------------------
# 一站式入口与闸门
# ---------------------------------------------------------------------------


class _FakeResult:
    """最小化的 Runner 结果替身：只需要 new_items 可迭代。"""

    def __init__(self, items):
        self.new_items = items


# 构造真实的 ToolCallOutputItem 需要一个 Agent 实例（用于内部弱引用），
# 这里用最小 Agent 即可，不会触发任何模型调用。
_DUMMY_AGENT = Agent(name="dummy", instructions="dummy")


def _result_with(outputs: list[str]) -> _FakeResult:
    """把一批工具输出字符串包装成 Runner 结果的形状。"""
    return _FakeResult(
        [
            ToolCallOutputItem(agent=_DUMMY_AGENT, raw_item="", output=output)
            for output in outputs
        ]
    )


def test_collect_kb_text_only_picks_knowledge_chunks():
    """只捞知识库分块，其余工具输出与空串都要被排除。"""
    result = _result_with(
        [KB_REFUND, KB_NOT_FOUND, "订单 A1001 已发货", ""]
    )
    collected = collect_kb_text(result)

    assert "refund_policy.txt" in collected
    assert "未找到" not in collected
    assert "A1001" not in collected


def test_check_premise_reports_skip_reasons():
    # 没有任何知识库依据
    assert check_premise("退款要30天吗", _FakeResult([])).skipped_reason == "no_kb_text"
    # 有依据，但问题里没有带单位的数字
    assert (
        check_premise("退款多久到账", _result_with([KB_REFUND])).skipped_reason
        == "no_mention"
    )
    # 两个前提都满足 -> 正常给出判定
    hit = check_premise("退款要30天吗", _result_with([KB_REFUND]))
    assert hit.skipped_reason is None
    assert hit.unverified == ["30"]
    assert hit.kb_sources == ["refund_policy.txt"]


def test_should_regenerate_gate():
    kb = KB_REFUND
    query = "退款要30天吗"

    # 全部条件满足
    ok, hits = should_regenerate(query, "是的，需要30天", kb, False, 0)
    assert ok is True and hits == ["30"]

    # 条件 2：模型没跟着说错
    assert should_regenerate(query, "请以政策为准", kb, False, 0)[0] is False
    # 条件 3：有写操作审批，优先级更高，必须让路
    assert should_regenerate(query, "需要30天", kb, True, 0)[0] is False
    # 条件 4：没有知识库依据
    assert should_regenerate(query, "需要30天", "", False, 0)[0] is False
    # 条件 5：已达重试上限
    assert should_regenerate(query, "需要30天", kb, False, 1, max_regen=1)[0] is False
