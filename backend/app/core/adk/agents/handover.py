"""
HandoverAgent — escalates conversations to human agents.

Sends a warm acknowledgment to the lead, updates the conversation status
to HUMAN_TAKEOVER, and (in future) notifies the team via Slack/email.
"""
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.adk.tools import make_escalate_to_human_tool
from app.models.models import ExecutionInstance


def build_handover_agent(
    session: AsyncSession,
    instance: ExecutionInstance,
) -> LlmAgent:
    """Build the human handover agent."""

    instruction = """You are the Human Handover Agent. Your job is to smoothly transfer the conversation to a human team member.

Steps:
1. Call escalate_to_human() with a warm, empathetic announcement message for the lead.
   Example: "I'm connecting you with one of our team members right now. They'll be with you shortly!"
2. Optionally call send_handover_summary() to give the human agent context about the conversation.
3. Be reassuring and professional. The lead should feel heard and helped, not handed off coldly.
"""

    async def send_handover_summary(summary: str) -> dict[str, Any]:
        """
        Send an internal summary of the conversation to help the human agent context.
        This is a future feature — currently a no-op that returns confirmation.
        Returns: {"status": "summary_noted"}
        """
        # Future: POST to internal webhook / Slack / email
        return {"status": "summary_noted", "summary_length": len(summary)}

    return LlmAgent(
        name="handover_agent",
        model=settings.GEMINI_MODEL,
        instruction=instruction,
        tools=[
            make_escalate_to_human_tool(session, instance),
            FunctionTool(func=send_handover_summary),
        ],
    )
