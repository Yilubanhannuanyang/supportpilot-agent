import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from supportpilot.db import (
    create_ticket_in_db,
    find_open_ticket_by_order_and_type,
    get_order_from_db,
)
from supportpilot.observability.tracer import get_current_trace_id
from supportpilot.rag.retriever import search_knowledge_base


SHIPPING_DEADLINE_HOURS = 48

APPROVAL_NOT_REQUIRED = "not_required"
APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"

WORKFLOW_LOG_PATH = Path("data/logs/workflow_trace.jsonl")

@dataclass
class ShippingWorkflowState:
    order_id: str

    order_found: bool = False
    shipping_status: str | None = None
    estimated_delivery: str | None = None
    hours_since_payment: int | None = None

    policy_found: bool = False
    policy_content: str | None = None

    is_overdue: bool = False

    ticket_created: bool = False
    ticket_id: str | None = None
    ticket_reused: bool = False

    approval_required: bool = False
    approval_status: str = "not_required"
    approval_action: str | None = None
    approval_reason: str | None = None

    current_step: str = "initialized"
    error: str | None = None

    trace: list[str] = field(default_factory=list)


def add_trace(
    state: ShippingWorkflowState,
    message: str,
) -> None:
    """记录 Workflow 执行轨迹。"""

    state.trace.append(message)
    print(f"[Trace] {message}")
def save_workflow_log(
    state: ShippingWorkflowState,
) -> None:
    """把一次 Workflow 的最终状态和 Trace 追加保存到 JSONL。"""

    WORKFLOW_LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    record = {
        "timestamp": datetime.now().isoformat(),
        "trace_id": get_current_trace_id(),  # OPT-013：串起三个日志的链路 ID
        "workflow": "shipping_workflow",
        "order_id": state.order_id,
        "current_step": state.current_step,
        "order_found": state.order_found,
        "policy_found": state.policy_found,
        "is_overdue": state.is_overdue,
        "ticket_created": state.ticket_created,
        "ticket_reused": state.ticket_reused,
        "ticket_id": state.ticket_id,
        "error": state.error,
        "trace": state.trace,
    }

    with WORKFLOW_LOG_PATH.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )

def check_order(
    state: ShippingWorkflowState,
) -> ShippingWorkflowState:
    """查询订单，并把结果写入 Workflow State。"""

    add_trace(
        state,
        f"check_order:start order_id={state.order_id}",
    )

    print(f"[Workflow] 正在查询订单：{state.order_id}")

    order_id = state.order_id.strip().upper()

    order = get_order_from_db(order_id)

    if order is None:
        state.order_found = False
        state.current_step = "order_not_found"
        state.error = "未找到对应订单。"

        print("[Workflow] 未找到订单。")

        add_trace(
            state,
            "check_order:failed order_not_found",
        )

        return state

    state.order_id = order_id
    state.order_found = True
    state.shipping_status = order["shipping_status"]
    state.estimated_delivery = order["estimated_delivery"]
    state.hours_since_payment = order["hours_since_payment"]
    state.current_step = "order_checked"

    add_trace(
        state,
        (
            "check_order:success "
            f"shipping_status={state.shipping_status}, "
            f"hours_since_payment={state.hours_since_payment}"
        ),
    )

    print(
        f"[Workflow] 订单查询成功："
        f"shipping_status={state.shipping_status}, "
        f"estimated_delivery={state.estimated_delivery}"
    )

    return state


def check_shipping_policy(
    state: ShippingWorkflowState,
) -> ShippingWorkflowState:
    """检索物流发货政策，并写入 Workflow State。"""

    add_trace(
        state,
        "check_shipping_policy:start",
    )

    print("[Workflow] 正在查询物流政策。")

    if not state.order_found:
        state.current_step = "policy_skipped"
        state.error = "订单不存在，无法继续查询物流政策。"

        print("[Workflow] 订单不存在，跳过物流政策查询。")

        add_trace(
            state,
            "check_shipping_policy:skipped order_not_found",
        )

        return state

    results = search_knowledge_base(
        query="已付款订单多久需要发货？如果超过时限应该怎么处理？",
        top_k=3,
    )

    if not results:
        state.policy_found = False
        state.current_step = "policy_not_found"
        state.error = "未找到足够相关的物流政策。"

        print("[Workflow] 未找到物流政策。")

        add_trace(
            state,
            "check_shipping_policy:failed policy_not_found",
        )

        return state

    state.policy_found = True
    state.policy_content = results[0]["content"]
    state.current_step = "policy_checked"

    add_trace(
        state,
        f"check_shipping_policy:success source={results[0]['source']}",
    )

    print(
        f"[Workflow] 已找到物流政策，"
        f"source={results[0]['source']}"
    )

    return state


def evaluate_shipping_delay(
    state: ShippingWorkflowState,
) -> ShippingWorkflowState:
    """根据确定性业务规则判断订单是否超时未发货。"""

    add_trace(
        state,
        "evaluate_shipping_delay:start",
    )

    print("[Workflow] 正在判断订单是否超时未发货。")

    if not state.order_found:
        state.current_step = "delay_check_skipped"
        state.error = "订单不存在，无法判断是否超时。"

        print("[Workflow] 订单不存在，跳过超时判断。")

        add_trace(
            state,
            "evaluate_shipping_delay:skipped order_not_found",
        )

        return state

    if not state.policy_found:
        state.current_step = "delay_check_skipped"
        state.error = "未找到物流政策，无法执行超时判断。"

        print("[Workflow] 缺少物流政策，跳过超时判断。")

        add_trace(
            state,
            "evaluate_shipping_delay:skipped policy_not_found",
        )

        return state

    if state.hours_since_payment is None:
        state.current_step = "delay_check_failed"
        state.error = "订单缺少付款时长数据。"

        print("[Workflow] 缺少付款时长数据。")

        add_trace(
            state,
            "evaluate_shipping_delay:failed missing_hours_since_payment",
        )

        return state

    if state.shipping_status != "等待仓库发货":
        state.is_overdue = False
        state.current_step = "delay_checked"

        print(
            "[Workflow] 订单已经发货或完成，"
            "不属于未发货超时。"
        )

        add_trace(
            state,
            "evaluate_shipping_delay:success is_overdue=False",
        )

        return state

    state.is_overdue = (
        state.hours_since_payment > SHIPPING_DEADLINE_HOURS
    )

    state.current_step = "delay_checked"

    add_trace(
        state,
        (
            "evaluate_shipping_delay:success "
            f"is_overdue={state.is_overdue}"
        ),
    )

    print(
        f"[Workflow] 已付款 {state.hours_since_payment} 小时，"
        f"发货时限 {SHIPPING_DEADLINE_HOURS} 小时，"
        f"is_overdue={state.is_overdue}"
    )

    return state
    if state.approval_status == APPROVAL_NOT_REQUIRED:
        state.approval_required = True
        state.approval_status = APPROVAL_PENDING
        state.approval_action = "create_shipping_ticket"
        state.approval_reason = (
            f"订单 {state.order_id} 已超出 "
            f"{SHIPPING_DEADLINE_HOURS} 小时发货时限，"
            "创建物流工单属于写操作，需要人工确认。"
        )
        state.current_step = "awaiting_approval"

        add_trace(
            state,
            "create_shipping_ticket:waiting_for_approval",
        )

        print(
            "[Workflow] 创建物流工单需要人工审批。"
        )

        return state

    if state.approval_status == APPROVAL_REJECTED:
        state.ticket_created = False
        state.current_step = "approval_rejected"

        add_trace(
            state,
            "create_shipping_ticket:rejected",
        )

        print(
            "[Workflow] 人工拒绝创建物流工单。"
        )

        return state

    if state.approval_status != APPROVAL_APPROVED:
        state.current_step = "awaiting_approval"

        return state

def create_shipping_ticket(
    state: ShippingWorkflowState,
) -> ShippingWorkflowState:
    """只有超时且人工批准后，才创建物流售后工单。"""

    add_trace(
        state,
        "create_shipping_ticket:start",
    )

    print("[Workflow] 正在判断是否需要创建物流工单。")

    # 1. 订单必须存在
    if not state.order_found:
        state.current_step = "ticket_skipped"
        state.error = "订单不存在，无法创建物流工单。"

        add_trace(
            state,
            "create_shipping_ticket:skipped order_not_found",
        )

        print("[Workflow] 订单不存在，跳过工单创建。")

        return state

    # 2. 必须已经完成超时判断
    if state.current_step != "delay_checked":
        state.current_step = "ticket_skipped"
        state.error = "尚未完成物流超时判断。"

        add_trace(
            state,
            "create_shipping_ticket:skipped delay_not_checked",
        )

        print("[Workflow] 尚未完成超时判断，跳过工单创建。")

        return state

    # 3. 没有超时，不需要创建
    if not state.is_overdue:
        state.ticket_created = False
        state.ticket_reused = False
        state.current_step = "completed"

        add_trace(
            state,
            "create_shipping_ticket:skipped not_overdue",
        )

        print("[Workflow] 订单未超时，不需要创建物流工单。")

        return state

    # 4. 先做幂等性检查
    existing_ticket = find_open_ticket_by_order_and_type(
        order_id=state.order_id,
        issue_type="物流超时",
    )

    if existing_ticket is not None:
        state.ticket_created = False
        state.ticket_reused = True
        state.ticket_id = f"T{existing_ticket['ticket_id']:04d}"
        state.current_step = "completed"

        add_trace(
            state,
            (
                "create_shipping_ticket:reused "
                f"ticket_id={state.ticket_id}"
            ),
        )

        print(
            f"[Workflow] 已存在未解决的物流工单："
            f"{state.ticket_id}，本次不重复创建。"
        )

        return state

    # 5. 第一次执行到这里：不创建，进入人工审批
    if state.approval_status == APPROVAL_NOT_REQUIRED:
        state.approval_required = True
        state.approval_status = APPROVAL_PENDING
        state.approval_action = "create_shipping_ticket"
        state.approval_reason = (
            f"订单 {state.order_id} 已付款 "
            f"{state.hours_since_payment} 小时，"
            f"超过 {SHIPPING_DEADLINE_HOURS} 小时发货时限。"
            "创建物流工单属于写操作，需要人工确认。"
        )
        state.current_step = "awaiting_approval"

        add_trace(
            state,
            "create_shipping_ticket:waiting_for_approval",
        )

        print("[Workflow] 创建物流工单需要人工审批。")

        return state

    # 6. 人工明确拒绝
    if state.approval_status == APPROVAL_REJECTED:
        state.ticket_created = False
        state.ticket_reused = False
        state.current_step = "approval_rejected"

        add_trace(
            state,
            "create_shipping_ticket:rejected",
        )

        print("[Workflow] 人工拒绝创建物流工单。")

        return state

    # 7. 只要不是 approved，就不能继续写数据库
    if state.approval_status != APPROVAL_APPROVED:
        state.current_step = "awaiting_approval"

        add_trace(
            state,
            "create_shipping_ticket:still_waiting_for_approval",
        )

        return state

    # 8. 只有人工批准后，才真正创建数据库工单
    ticket_id = create_ticket_in_db(
        order_id=state.order_id,
        issue_type="物流超时",
        description=(
            f"订单 {state.order_id} 已付款 "
            f"{state.hours_since_payment} 小时，"
            f"仍处于“{state.shipping_status}”状态，"
            f"超过 {SHIPPING_DEADLINE_HOURS} 小时发货时限。"
        ),
    )

    state.ticket_created = True
    state.ticket_reused = False
    state.ticket_id = f"T{ticket_id:04d}"

    state.approval_required = False
    state.current_step = "completed"

    add_trace(
        state,
        f"create_shipping_ticket:success ticket_id={state.ticket_id}",
    )

    print(
        f"[Workflow] 人工审批通过，物流工单创建成功："
        f"{state.ticket_id}"
    )

    return state


def run_shipping_workflow(
    order_id: str,
) -> ShippingWorkflowState:
    """执行完整的物流异常处理 Workflow。"""

    print("=" * 50)
    print(f"[Workflow] 开始处理订单：{order_id}")
    print("=" * 50)

    state = ShippingWorkflowState(
        order_id=order_id,
    )

    add_trace(
        state,
        "workflow:started",
    )

    try:
        state = check_order(state)

        if not state.order_found:
            add_trace(
                state,
                "workflow:stopped order_not_found",
            )

            print("[Workflow] Workflow 提前结束：订单不存在。")

            save_workflow_log(state)

            return state

        state = check_shipping_policy(state)

        if not state.policy_found:
            add_trace(
                state,
                "workflow:stopped policy_not_found",
            )

            print("[Workflow] Workflow 提前结束：未找到物流政策。")

            save_workflow_log(state)

            return state

        state = evaluate_shipping_delay(state)

        if state.current_step != "delay_checked":
            add_trace(
                state,
                "workflow:stopped delay_check_failed",
            )

            print("[Workflow] Workflow 提前结束：超时判断失败。")

            save_workflow_log(state)

            return state

        state = create_shipping_ticket(state)

        add_trace(
            state,
            f"workflow:finished current_step={state.current_step}",
        )

        save_workflow_log(state)

        print("=" * 50)
        print(
            f"[Workflow] Workflow 结束，"
            f"current_step={state.current_step}"
        )
        print("=" * 50)

        return state

    except Exception as exc:
        state.current_step = "failed"
        state.error = str(exc)

        add_trace(
            state,
            (
                "workflow:failed "
                f"error={type(exc).__name__}: {exc}"
            ),
        )

        print(
            f"[Workflow] Workflow 执行失败："
            f"{type(exc).__name__}: {exc}"
        )

        save_workflow_log(state)

        return state

def approve_shipping_ticket(
    state: ShippingWorkflowState,
) -> ShippingWorkflowState:
    """人工批准待审批的物流工单创建请求。"""

    if state.current_step != "awaiting_approval":
        state.error = "当前 Workflow 不在待审批状态。"

        add_trace(
            state,
            "approval:failed not_awaiting_approval",
        )

        print("[HITL] 当前没有待审批的操作。")

        return state

    if state.approval_action != "create_shipping_ticket":
        state.error = "当前待审批动作不是创建物流工单。"

        add_trace(
            state,
            "approval:failed invalid_action",
        )

        print("[HITL] 待审批动作不匹配。")

        return state

    state.approval_status = APPROVAL_APPROVED
    state.approval_required = False
    state.error = None

    add_trace(
        state,
        "approval:approved action=create_shipping_ticket",
    )

    print("[HITL] 人工已批准创建物流工单。")

    # 恢复到写操作前的状态，继续执行创建工单
    state.current_step = "delay_checked"

    state = create_shipping_ticket(state)

    save_workflow_log(state)

    return state

def reject_shipping_ticket(
    state: ShippingWorkflowState,
) -> ShippingWorkflowState:
    """人工拒绝待审批的物流工单创建请求。"""

    if state.current_step != "awaiting_approval":
        state.error = "当前 Workflow 不在待审批状态。"

        add_trace(
            state,
            "approval:failed not_awaiting_approval",
        )

        print("[HITL] 当前没有待审批的操作。")

        return state

    if state.approval_action != "create_shipping_ticket":
        state.error = "当前待审批动作不是创建物流工单。"

        add_trace(
            state,
            "approval:failed invalid_action",
        )

        print("[HITL] 待审批动作不匹配。")

        return state

    state.approval_status = APPROVAL_REJECTED
    state.approval_required = False
    state.ticket_created = False
    state.ticket_reused = False
    state.current_step = "approval_rejected"
    state.error = None

    add_trace(
        state,
        "approval:rejected action=create_shipping_ticket",
    )

    print("[HITL] 人工已拒绝创建物流工单。")

    save_workflow_log(state)

    return state
 