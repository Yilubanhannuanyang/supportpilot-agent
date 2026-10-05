"""统一的链路 ID（trace_id）生成与传递。

用途：把原本互不关联的三个日志文件串起来 ——
    data/logs/rag_retrieval.jsonl
    data/logs/workflow_trace.jsonl
    data/logs/approval_log.jsonl
这样用户投诉"上一条答错了"时，能按 trace_id 还原那一次的完整链路。

★ 为什么用 contextvars 而不是模块级全局变量？
   run.py 是 asyncio 驱动的，多个请求可能交错执行。
   模块级全局变量会被后一轮覆盖，导致日志串号；contextvars 是
   Python 官方为异步场景提供的上下文隔离机制，每个执行上下文各持一份。
"""

import contextvars
import uuid

_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id",
    default=None,
)


def new_trace_id() -> str:
    """生成一个新的链路 ID，例如 tr-9f3a1c2b。"""
    return f"tr-{uuid.uuid4().hex[:8]}"


def set_current_trace_id(trace_id: str) -> None:
    """把当前执行上下文的链路 ID 设为指定值（每轮对话开始时调用）。"""
    _current_trace_id.set(trace_id)


def get_current_trace_id() -> str | None:
    """取当前执行上下文的链路 ID。

    三个日志写入函数都调用它。返回 None 表示"不在任何一轮对话里"
    （例如直接在命令行跑 retriever 时），此时日志里会写 null，不影响功能。
    """
    return _current_trace_id.get()
