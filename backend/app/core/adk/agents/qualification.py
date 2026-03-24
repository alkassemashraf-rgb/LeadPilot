"""
QualificationAgent — drives lead qualification dialogue.

Knows all workspace qualification questions and criteria, tracks progress
via ADK session state, and marks the lead qualified or disqualified when
enough information is collected.
"""
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.adk.tools import make_tag_contact_tool
from app.models.models import Contact, ExecutionInstance


def build_qualification_agent(
    qualification_questions: list[dict],
    qualification_criteria: list[dict],
    session: AsyncSession,
    instance: ExecutionInstance,
) -> LlmAgent:
    """
    Build the lead qualification agent for a workspace.

    Qualification questions and criteria are injected at build time so the
    agent's instruction is fully compiled without runtime tool calls.
    """
    questions_text = "\n".join(
        f"- {q['label']}"
        for q in sorted(qualification_questions, key=lambda q: q.get("order", 0))
        if q.get("enabled", True)
    ) or "(no questions configured)"

    criteria_text = "\n".join(
        f"- {c['label']}: {c.get('description', '')}"
        for c in sorted(qualification_criteria, key=lambda c: c.get("sort_order", 0))
        if c.get("is_enabled", True)
    ) or "(no criteria configured)"

    instruction = f"""You are the Lead Qualification Agent for this business.

Your ONLY job is to collect the following information from the lead through natural conversation:
{questions_text}

Evaluate against these criteria to decide if the lead is qualified:
{criteria_text}

Rules:
- Ask ONE question at a time. Never ask multiple questions in one message.
- Be conversational and friendly. Never sound like a form.
- Once all required information is collected, call mark_qualified() or mark_disqualified()
  based on the criteria above.
- If the lead asks to speak to a human at any point, stop and signal that escalation is needed.
- Do NOT send messages yourself — use ask_followup_question() to surface the next question
  and the ReplyAgent will send it.
"""

    async def ask_followup_question(question: str) -> dict[str, Any]:
        """
        Signal that the next qualification question should be sent to the lead.
        The orchestrator will route this to the ReplyAgent to deliver.
        Returns: {"next_question": "<text>", "action": "send_to_lead"}
        """
        return {"next_question": question, "action": "send_to_lead"}

    async def mark_qualified(reason: str) -> dict[str, Any]:
        """
        Mark this lead as qualified based on the information collected.
        Call this when all qualification criteria are met.
        Returns: {"qualification_status": "qualified", "reason": "<text>"}
        """
        contact = await session.get(Contact, instance.contact_id)
        if contact:
            contact.qualification_status = "qualified"
            meta = dict(contact.additional_metadata or {})
            tags: list[str] = meta.get("tags", [])
            if "qualified" not in tags:
                tags.append("qualified")
            meta["tags"] = tags
            contact.additional_metadata = meta
            session.add(contact)
            await session.commit()
        return {"qualification_status": "qualified", "reason": reason}

    async def mark_disqualified(reason: str) -> dict[str, Any]:
        """
        Mark this lead as disqualified.
        Call this when the lead does not meet the qualification criteria.
        Returns: {"qualification_status": "disqualified", "reason": "<text>"}
        """
        contact = await session.get(Contact, instance.contact_id)
        if contact:
            contact.qualification_status = "disqualified"
            meta = dict(contact.additional_metadata or {})
            tags: list[str] = meta.get("tags", [])
            if "disqualified" not in tags:
                tags.append("disqualified")
            meta["tags"] = tags
            contact.additional_metadata = meta
            session.add(contact)
            await session.commit()
        return {"qualification_status": "disqualified", "reason": reason}

    return LlmAgent(
        name="qualification_agent",
        model=settings.GEMINI_MODEL,
        instruction=instruction,
        tools=[
            FunctionTool(func=ask_followup_question),
            FunctionTool(func=mark_qualified),
            FunctionTool(func=mark_disqualified),
            make_tag_contact_tool(session, instance),
        ],
    )
