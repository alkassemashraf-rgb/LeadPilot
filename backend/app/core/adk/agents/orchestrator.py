"""
OrchestratorAgent — entry point for every inbound message in M-B+.

Routes conversations to specialized sub-agents based on lead state:
- Unqualified  → QualificationAgent
- Qualified, CRM unsynced → CRMAgent then ReplyAgent
- Qualified, CRM synced  → ReplyAgent
- Human requested        → HandoverAgent
"""
from uuid import UUID

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.models import (
    ChannelIdentity,
    Contact,
    Conversation,
    ExecutionInstance,
    QualificationConfig,
    QualificationCriterion,
)
from app.services.prompt_compiler import compile_workspace_prompt

from app.core.adk.agents.qualification import build_qualification_agent
from app.core.adk.agents.crm import build_crm_agent
from app.core.adk.agents.reply import build_reply_agent
from app.core.adk.agents.handover import build_handover_agent


async def build_orchestrator(
    workspace_id: UUID,
    contact_id: UUID,
    conversation_id: UUID,
    session: AsyncSession,
    instance: ExecutionInstance,
) -> LlmAgent:
    """
    Build the full multi-agent graph for one conversation turn.

    Reads current lead state (qualification_status, zoho_lead_id, platform)
    and injects it into the orchestrator's routing instruction so every
    delegation decision is context-aware.
    """
    # 1. Workspace business context
    compiled = await compile_workspace_prompt(
        workspace_id,
        session,
        include_qualification=True,
    )

    # 2. Contact + conversation state
    contact = await session.get(Contact, contact_id)
    conversation = await session.get(Conversation, conversation_id)

    is_qualified = (contact.qualification_status == "qualified") if contact else False
    crm_synced = bool(contact.zoho_lead_id) if contact else False

    # 3. Platform — first ChannelIdentity for this contact
    identity_result = await session.execute(
        select(ChannelIdentity).where(ChannelIdentity.contact_id == contact_id).limit(1)
    )
    identity = identity_result.scalars().first()
    platform = identity.provider if identity else "whatsapp"

    # 4. Qualification questions + criteria (structured, not from compiled text)
    config_result = await session.execute(
        select(QualificationConfig).where(QualificationConfig.workspace_id == workspace_id)
    )
    qual_config = config_result.scalars().first()
    qualification_questions: list[dict] = (
        qual_config.qualification_questions if qual_config else []
    )

    criteria_result = await session.execute(
        select(QualificationCriterion)
        .where(
            QualificationCriterion.workspace_id == workspace_id,
            QualificationCriterion.is_enabled.is_(True),
        )
        .order_by(QualificationCriterion.sort_order)
    )
    qualification_criteria = [
        {"label": c.label, "description": c.description, "is_enabled": c.is_enabled}
        for c in criteria_result.scalars().all()
    ]

    # 5. Build sub-agents
    qualification_agent = build_qualification_agent(
        qualification_questions=qualification_questions,
        qualification_criteria=qualification_criteria,
        session=session,
        instance=instance,
    )
    crm_agent = build_crm_agent(session=session, instance=instance)
    reply_agent = build_reply_agent(platform=platform, session=session, instance=instance)
    handover_agent = build_handover_agent(session=session, instance=instance)

    # 6. Orchestrator instruction with injected state
    orchestrator_instruction = f"""You are the Conversation Orchestrator for this business's AI system.

Current lead state:
- Qualification status: {"qualified" if is_qualified else "not yet qualified"}
- CRM synced to Zoho: {"yes" if crm_synced else "no"}

Routing rules (follow in order):
1. If the lead explicitly requests a human or expresses strong frustration → delegate to handover_agent immediately.
2. If the lead is NOT yet qualified → delegate to qualification_agent to collect required information.
   After qualification_agent finishes, delegate to reply_agent to send the next question or confirmation.
3. If the lead IS qualified and CRM is NOT yet synced → delegate to crm_agent to sync, then delegate to reply_agent.
4. If the lead IS qualified and CRM IS synced → delegate to reply_agent to handle the conversation.
5. After any sub-agent completes its task, always end the turn by delegating to reply_agent to send a response.

Business context and tone:
{compiled.system_instruction}
"""

    return LlmAgent(
        name="orchestrator",
        model=settings.GEMINI_MODEL,
        instruction=orchestrator_instruction,
        tools=[
            AgentTool(agent=qualification_agent),
            AgentTool(agent=crm_agent),
            AgentTool(agent=reply_agent),
            AgentTool(agent=handover_agent),
        ],
    )
