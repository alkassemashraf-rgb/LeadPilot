"""
ReplyAgent — crafts and sends messages to the lead.

The single agent responsible for all outbound communication.
The orchestrator delegates final replies here after any sub-agent completes work.
"""
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.adk.tools import make_send_reply_tool
from app.models.models import ExecutionInstance


def build_reply_agent(
    platform: str,
    session: AsyncSession,
    instance: ExecutionInstance,
) -> LlmAgent:
    """
    Build the reply agent for a specific platform.

    Args:
        platform: Messaging platform ("whatsapp" | "messenger" | "instagram")
        session: DB session (bound via closure)
        instance: Current execution instance (bound via closure)
    """
    instruction = f"""You are the Reply Agent. Your ONLY job is to craft and send messages to the lead on {platform}.

Rules:
- Keep WhatsApp messages under 160 characters unless detail is genuinely required.
- Match the business tone from the conversation context.
- Never send multiple messages when one will do.
- Use send_reply() for all text messages.
- Use send_media_message() only when an image or document is explicitly needed.
- Always send at least one message — never return without sending.
"""

    async def send_media_message(media_url: str, caption: str = "") -> dict[str, Any]:
        """
        Send an image or document to the lead.
        Use only when a visual asset is explicitly required.
        Returns: {"status": "not_supported"}
        """
        # Placeholder — full media dispatch will be wired in a future mission
        return {"status": "not_supported"}

    return LlmAgent(
        name="reply_agent",
        model=settings.GEMINI_MODEL,
        instruction=instruction,
        tools=[
            make_send_reply_tool(session, instance),
            FunctionTool(func=send_media_message),
        ],
    )
