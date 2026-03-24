"""
CRMAgent — synchronizes lead data to Zoho CRM.

A background-only agent: it never sends messages to the lead.
It is invoked by the orchestrator when a lead becomes qualified and
CRM sync hasn't happened yet (or when an explicit sync is requested).
"""
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.adk.tools import make_upsert_zoho_lead_tool
from app.models.models import Contact, ExecutionInstance


def build_crm_agent(
    session: AsyncSession,
    instance: ExecutionInstance,
) -> LlmAgent:
    """Build the CRM sync agent. Does not interact with the lead directly."""

    instruction = """You are the CRM Sync Agent. Your sole job is to synchronize lead data to Zoho CRM.

When invoked:
1. Call upsert_zoho_lead() to create or update the lead record in Zoho.
2. If a specific field needs updating, call update_contact_field() first.
3. Report back what was synced (lead ID and action: create or update).
4. Do NOT send any messages to the lead — this is a background operation only.
"""

    async def update_contact_field(field_name: str, value: str) -> dict[str, Any]:
        """
        Update a named field on the contact record before CRM sync.
        Supported fields: first_name, last_name, display_name.
        Returns: {"field": "<name>", "updated": true}
        """
        contact = await session.get(Contact, instance.contact_id)
        if contact and hasattr(contact, field_name):
            setattr(contact, field_name, value)
            session.add(contact)
            await session.commit()
            return {"field": field_name, "updated": True}
        return {"field": field_name, "updated": False}

    return LlmAgent(
        name="crm_agent",
        model=settings.GEMINI_MODEL,
        instruction=instruction,
        tools=[
            make_upsert_zoho_lead_tool(session, instance),
            FunctionTool(func=update_contact_field),
        ],
    )
