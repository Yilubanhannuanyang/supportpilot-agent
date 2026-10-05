from agents import Agent

from supportpilot.config import create_model
from supportpilot.prompt_loader import load_instructions
from supportpilot.tools.kb_tools import search_knowledge_base
from supportpilot.tools.order_tools import get_order_status
from supportpilot.tools.ticket_tools import (
    create_ticket,
    get_ticket_status,
    update_ticket_status,
)


def create_support_agent() -> Agent:
    """组装 SupportPilot Agent。

    提示词不写在这里：正文维护在 prompts/support_agent.yaml，按 block 组织，
    改动措辞只需编辑 YAML，无需触碰代码。
    """

    model = create_model()

    return Agent(
        name="SupportPilot",
        instructions=load_instructions(),
        model=model,
        tools=[
            get_order_status,
            create_ticket,
            get_ticket_status,
            update_ticket_status,
            search_knowledge_base,
        ],
    )


# ---------------------------------------------------------------------------
# prompts/support_agent.yaml 的 block 与防御目标对照
#
# 提示词正文已外置到 prompts/support_agent.yaml，每个 block 对应一条约束：
#
#   1. 避免模型反复跟用户确认编号类型      -> numbering
#   2. 避免模型编造订单信息                -> data_grounding
#   3. 避免模型凭常识回答企业政策          -> policy_grounding
#   4. 避免模型编造引用来源                -> source_citation
#   5. 信息不全时先追问而不是直接开单      -> ticket_create
#   6. 避免模型假称写操作已完成            -> write_approval
#   7. 避免模型被用户的错误前提带跑        -> premise_check
# ---------------------------------------------------------------------------
