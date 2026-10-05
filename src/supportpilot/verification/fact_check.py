"""生成层前提校验：检查用户陈述中的数字是否有知识库依据。

背景
----
企业政策问答里有一类问题检索层无法解决：用户带着**错误前提**提问，例如
「我听说你们退款要30天是真的吗」，而知识库原文写的是「银行卡退款到账时间
通常为 3 至 7 个工作日」。

这类问题的检索结果是**正确的**（top1 命中 refund_policy.txt，距离 0.4438），
所以它不是检索缺陷：距离度量的是"话题相关度"，而非"主张是否为真"。
想靠调阈值拦住它，可用窗口只有 [0.4379, 0.4438)、宽 0.0059，
而 0.40 时真实业务问题已经误杀 4/10 —— 工具选错了，不是参数没调好。

因此本模块在**生成层**补一层确定性兜底。

核心判据
--------
校验对象是**用户问题里提到的数字**，不是答案里的数字
（答案里会有订单号 A1001、工单号 T0001、日期等大量合法数字，校验答案必然误报）。

    用户提到的「数字+单位」的数值，如果在本次检索到的知识库原文里找不到，
    就说明用户的前提可能记错了 -> 打标记。

该判据同时覆盖两类问题：
    「退款要 30 天」 -> 原文写 3~7        -> 冲突
    「签收 8 天还能退吗」 -> 原文写 7 天    -> 冲突（政策边界）

本模块不做写操作、不调用 LLM，纯正则，可单测。
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from agents.items import ToolCallOutputItem

from supportpilot.observability.tracer import get_current_trace_id

# 是否在答案末尾追加中性提示。设为 False 则只打控制台与日志、不改写答案。
ENABLE_PREMISE_HINT = True

# 日志落绝对路径，避免依赖"必须在项目根目录运行"。
# src/supportpilot/verification/fact_check.py -> parents[3] = 项目根
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = _PROJECT_ROOT / "data" / "logs" / "premise_conflict.jsonl"

# ---------------------------------------------------------------------------
# 正则
# ---------------------------------------------------------------------------

# 单位白名单。长单位必须排在短单位前面，否则「个工作日」会被「个」抢先匹配。
_UNIT = r"个工作日|工作日|小时|分钟|个月|天|日|个|月|年|次|元|分|秒|%"

# 用户侧：严格。要求数字紧邻单位，且左侧不能是字母或数字
# —— 后者用于排除订单号 A1001、工单号 T0001、链路 ID tr-9f3a1c2b。
_USER_NUMBER_RE = re.compile(
    r"(?<![0-9A-Za-z])(\d+)\s*(" + _UNIT + r")"
)

# 知识库侧：宽松。取所有数字作为"已知集合"（宁可多收，避免误报）。
# 注意数字与单位之间可能是空格，例如「48 小时」「7 天内」「3 至 7 个工作日」。
# 所以这里不能要求数字紧邻单位 —— 早期版本用 (?=[天日个…]) 前瞻断言，
# 在真实知识库上一条都匹配不到，会导致已知集合为空、100% 误报。
_KB_NUMBER_RE = re.compile(r"\d+")

# 行首列表序号（"1. " "2. "），必须在抽取前剥掉，
# 否则这些序号会被当成政策数字，让 1~6 永远不被标记（漏报）。
_KB_LIST_MARKER_RE = re.compile(r"(?m)^\s*\d+\.\s*")

# 中文区间写法：「1 至 3 个工作日」「3-7天」「3 到 7 天」
_KB_RANGE_RE = re.compile(r"(\d+)\s*(?:至|到|-|~)\s*(\d+)")

# 知识库工具输出的分块格式，与 tools/kb_tools.py 里的 "\n\n".join(...) 严格对应。
# ⚠️ 若 kb_tools.py 改变了输出格式，此处需同步修改（单测已锁死该格式）。
_KB_CHUNK_RE = re.compile(
    r"\[资料\s*\d+\]\s*来源：(?P<source>[^\n]+)\s*内容：(?P<content>.*?)(?=\n\s*\[资料|\Z)",
    re.S,
)

# 区间展开上限，防止「1000000 至 2000000」这类异常写法撑爆内存。
_MAX_RANGE_SPAN = 500


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NumberMention:
    """用户提到的一处「数字+单位」。"""

    raw: str  # 原文片段，例如 "30 天"
    value: str  # 归一化后的数值，例如 "30"
    unit: str  # 单位，例如 "天"


@dataclass
class FactCheckResult:
    """一次前提校验的完整结果。"""

    mentions: list[NumberMention] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)  # ★ 强标记：值在原文中完全找不到
    kb_sources: list[str] = field(default_factory=list)
    kb_numbers: list[str] = field(default_factory=list)  # 原文中的已知数字，便于复盘误报
    skipped_reason: str | None = None  # "no_kb_text" | "no_mention" | "unparsed_kb_text"


# ---------------------------------------------------------------------------
# 抽取
# ---------------------------------------------------------------------------


def extract_user_numbers(text: str) -> list[NumberMention]:
    """从用户问题中抽取「数字+单位」，严格模式。

    只认带单位的数字，从而自动过滤订单号、工单号、链路 ID 等不含单位的编号。
    """
    if not text:
        return []

    mentions: list[NumberMention] = []
    for match in _USER_NUMBER_RE.finditer(text):
        mentions.append(
            NumberMention(
                raw=match.group(0),
                value=match.group(1),
                unit=match.group(2),
            )
        )
    return mentions


def collect_kb_text(result) -> str:
    """从 Runner 运行结果里捞出知识库工具返回的原文。

    不依赖工具名识别：agents 0.22.3 的 ToolCallOutputItem 没有 name 字段，
    因此改用输出格式特征判断（知识库工具输出形如 "[资料 1]\\n来源：...\\n内容：..."）。

    知识库无命中时工具返回 "知识库中未找到相关内容。"，不含 "[资料"，
    会被自动排除，collect 结果为空串 —— 调用方据此走跳过分支。
    """
    texts: list[str] = []

    for item in getattr(result, "new_items", None) or []:
        if not isinstance(item, ToolCallOutputItem):
            continue

        output = item.output
        if not isinstance(output, str):
            continue

        if "[资料" in output and "来源：" in output:
            texts.append(output)

    return "\n\n".join(texts)


def parse_kb_chunks(kb_text: str) -> list[dict]:
    """把知识库工具输出切成 [{source, content}, ...]。

    解析不出任何分块时返回空列表，调用方应视为"没有可用依据"并跳过校验，
    以免在格式变动时产生大量误报。
    """
    if not kb_text:
        return []

    return [
        {"source": match.group("source").strip(), "content": match.group("content")}
        for match in _KB_CHUNK_RE.finditer(kb_text)
    ]


def extract_known_numbers(chunks: list[dict]) -> set[str]:
    """从知识库分块中抽取"已知数字"集合。

    三步（缺一不可）：
        ① 剥掉行首列表序号（"1. " "2. "）—— 否则 1~6 会被误当政策数字
        ② 展开中文区间（"3 至 7 个工作日" -> 3,4,5,6,7）
        ③ 取所有阿拉伯数字

    刻意宽松：知识库侧宁可多收，避免把真实政策数字漏掉而误报用户。
    代价是落在政策区间内的数字（如 5 天）不会被标记 —— 这是
    "用召回换精度"的取舍，漏掉的部分由 OPT-005 的 Prompt 约束覆盖。
    """
    numbers: set[str] = set()

    for chunk in chunks:
        content = _KB_LIST_MARKER_RE.sub(" ", chunk.get("content", ""))

        for low, high in _KB_RANGE_RE.findall(content):
            start, end = int(low), int(high)
            if 0 <= end - start <= _MAX_RANGE_SPAN:
                numbers.update(str(value) for value in range(start, end + 1))
            else:
                numbers.update({low, high})

        numbers.update(_KB_NUMBER_RE.findall(content))

    return numbers


def find_unverified_numbers(user_query: str, kb_text: str) -> list[str]:
    """返回「用户提到、但知识库原文里找不到」的数值列表（升序）。

    这是本模块的主入口，也是单测的主入口。
    """
    if not kb_text or not kb_text.strip():
        return []

    mentions = extract_user_numbers(user_query)
    if not mentions:
        return []

    chunks = parse_kb_chunks(kb_text)
    if not chunks:
        # 输出格式不符合预期 -> 无可用依据 -> 跳过，宁可不报也不误报
        return []

    known = extract_known_numbers(chunks)
    unknown = {mention.value for mention in mentions} - known - {"0"}

    return sorted(unknown, key=int)


# ---------------------------------------------------------------------------
# 一站式入口
# ---------------------------------------------------------------------------


def check_premise(user_query: str, result) -> FactCheckResult:
    """从 Runner 结果出发完成一次完整校验。"""
    kb_text = collect_kb_text(result)

    if not kb_text.strip():
        return FactCheckResult(skipped_reason="no_kb_text")

    mentions = extract_user_numbers(user_query)
    if not mentions:
        return FactCheckResult(skipped_reason="no_mention")

    chunks = parse_kb_chunks(kb_text)
    if not chunks:
        return FactCheckResult(skipped_reason="unparsed_kb_text")

    known = extract_known_numbers(chunks)

    return FactCheckResult(
        mentions=mentions,
        unverified=sorted(
            {mention.value for mention in mentions} - known - {"0"},
            key=int,
        ),
        kb_sources=[chunk["source"] for chunk in chunks],
        kb_numbers=sorted(known, key=int),
    )


def format_premise_hint(numbers: list[str]) -> str:
    """生成追加到答案末尾的中性提示。

    措辞刻意保持中性：说"未在知识库原文中出现"，而不是"你说错了"。
    像「签收 8 天还能无理由退货吗」这类问题里，8 天是用户自己的事实陈述，
    并不是错误主张，用"前提有误"来表述既不准确也不礼貌。
    """
    joined = "、".join(numbers)
    return (
        f"\n\n（系统提示：你提到的「{joined}」未在知识库检索到的政策原文中出现，"
        f"以上回答以知识库原文为准。）"
    )


def log_premise_conflict(
    query: str,
    result: FactCheckResult,
    *,
    answer_before: str = "",
    answer_after: str = "",
    mode: str = "hint",
) -> None:
    """把一次前提校验结果追加到 SQLite 外的 JSONL 日志。"""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now().isoformat(),
        "trace_id": get_current_trace_id(),
        "query": query,
        "unverified_numbers": result.unverified,
        "user_mentions": [mention.raw for mention in result.mentions],
        "kb_sources": result.kb_sources,
        "kb_numbers": result.kb_numbers,
        "mode": mode,
        "stage": "mvp",
        "answer_before": answer_before,
        "answer_after": answer_after,
    }

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# 预留：自动重生成闸门（v0.2，当前 run.py 不调用）
# ---------------------------------------------------------------------------


def should_regenerate(
    user_query: str,
    answer: str,
    kb_text: str,
    has_approval_request: bool,
    retry_count: int,
    max_regen: int = 1,
) -> tuple[bool, list[str]]:
    """判断是否值得触发一次自动重生成，返回 (是否重生成, 可疑数字)。

    5 个条件必须全部满足，任何一条放宽都会退化成"每次提到数字就重算"。

    ⚠️ 本轮（v0.1）不接线到 run.py，原因：
        ① 一次重生成 = 一次额外模型往返，成本翻倍且难以说清；
        ② 重跑模型可能再次触发写操作，属写库级别的失败模式；
        ③ 它改的是主循环最敏感的一段，另有 result 必须替换、
           conversation 只追加最终答案、修正消息不能入库等多个易错点；
        ④ 先用日志统计检出率与误报率，再决定是否加大干预更稳妥。

    v0.2 若启用，必须使用 result.to_input_list()（而非 conversation）重跑，
    否则模型看不到上一轮的工具产出，会重新检索一次。
    """
    if retry_count >= max_regen:
        return False, []
    if has_approval_request:
        return False, []
    if not kb_text or not kb_text.strip():
        return False, []

    suspicious = find_unverified_numbers(user_query, kb_text)
    if not suspicious:
        return False, []

    # 模型自己没跟着说错，就没有必要重算
    if not any(number in answer for number in suspicious):
        return False, []

    return True, suspicious
