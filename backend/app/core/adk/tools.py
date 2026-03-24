"""
ADK tool factory for LeadPilot.

Each tool is a plain async function whose parameters are visible to the LLM.
The DB session and execution instance are pre-bound via closure — the LLM
never sees them.

Individual factory functions (make_*_tool) allow sub-agents to reuse specific
tools without pulling the full M-A flat set.
"""
import logging
from typing import Any

from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    Contact,
    Conversation,
    ConversationStatus,
    ExecutionInstance,
)
from app.domain.runtime import handle_send_message, handle_zoho_upsert
from app.services.runtime_event_service import log_event

logger = logging.getLogger(__name__)


# ── Individual tool factories ──────────────────────────────────────────────


def make_send_reply_tool(session: AsyncSession, instance: ExecutionInstance) -> FunctionTool:
    async def send_reply(message_content: str) -> dict[str, Any]:
        """
        Send a text reply to the contact on their messaging platform (WhatsApp or Meta).
        Use this when you want to respond to the lead with a message.
        Returns: {"status": "sent"}
        """
        await handle_send_message(session, instance, {"content": message_content})
        return {"status": "sent"}

    return FunctionTool(func=send_reply)


def make_upsert_zoho_lead_tool(session: AsyncSession, instance: ExecutionInstance) -> FunctionTool:
    async def upsert_zoho_lead() -> dict[str, Any]:
        """
        Sync the contact's current data to Zoho CRM as a lead.
        Use this when enough information has been collected to create or update a CRM record.
        Returns: {"zoho_lead_id": "...", "action": "create" or "update"}
        """
        return await handle_zoho_upsert(session, instance, {})

    return FunctionTool(func=upsert_zoho_lead)


def make_escalate_to_human_tool(session: AsyncSession, instance: ExecutionInstance) -> FunctionTool:
    async def escalate_to_human(announcement_message: str) -> dict[str, Any]:
        """
        Transfer the conversation to a human agent and send an announcement message.
        Use this when the lead requests a human, expresses frustration, or when you
        cannot resolve their query.
        Returns: {"status": "escalated"}
        """
        conv_result = await session.execute(
            select(Conversation).where(Conversation.contact_id == instance.contact_id)
        )
        conversation = conv_result.scalars().first()
        if conversation:
            conversation.status = ConversationStatus.HUMAN_TAKEOVER
            session.add(conversation)
            await log_event(
                session,
                event_type="runtime.human_escalation",
                source="adk_tool",
                workspace_id=instance.workspace_id,
                related_ids={
                    "execution_instance_id": str(instance.id),
                    "contact_id": str(instance.contact_id),
                },
            )

        await handle_send_message(session, instance, {"content": announcement_message})
        await session.commit()
        return {"status": "escalated"}

    return FunctionTool(func=escalate_to_human)


def make_tag_contact_tool(session: AsyncSession, instance: ExecutionInstance) -> FunctionTool:
    async def tag_contact(tag: str) -> dict[str, Any]:
        """
        Apply a classification tag to the contact for segmentation.
        Use this after determining a lead's category, intent, or qualification status.
        Returns: {"tag": "...", "applied": true}
        """
        contact = await session.get(Contact, instance.contact_id)
        if contact:
            meta = dict(contact.additional_metadata or {})
            tags: list[str] = meta.get("tags", [])
            if tag not in tags:
                tags.append(tag)
            meta["tags"] = tags
            contact.additional_metadata = meta
            session.add(contact)
            await session.commit()

        return {"tag": tag, "applied": True}

    return FunctionTool(func=tag_contact)


# ── Composite factory (M-A flat mode — kept for backward compatibility) ────


def make_tools(session: AsyncSession, instance: ExecutionInstance) -> list[FunctionTool]:
    """
    Build the four ADK FunctionTools for a conversation turn (single-agent mode).
    Used by build_leadpilot_agent() and M-A tests.
    """
    return [
        make_send_reply_tool(session, instance),
        make_upsert_zoho_lead_tool(session, instance),
        make_escalate_to_human_tool(session, instance),
        make_tag_contact_tool(session, instance),
    ]
