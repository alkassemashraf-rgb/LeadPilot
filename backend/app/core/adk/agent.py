"""
Single-agent mode factory — kept for tests and Prompt Studio.
Production uses build_orchestrator() from app.core.adk.agents.orchestrator.
"""
from uuid import UUID

from google.adk.agents import LlmAgent
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.adk.tools import make_tools
from app.models.models import ExecutionInstance
from app.services.prompt_compiler import compile_workspace_prompt


async def build_leadpilot_agent(
    workspace_id: UUID,
    session: AsyncSession,
    execution_instance: ExecutionInstance,
    inbound_message: str,
) -> LlmAgent:
    """
    Build a fully configured LlmAgent for a workspace conversation.

    Compiles the workspace system instruction (prompt, knowledge, qualification),
    wires the four ADK tools with DB session bound via closure, and returns
    a ready-to-run LlmAgent.
    """
    compiled = await compile_workspace_prompt(
        workspace_id,
        session,
        include_files=True,
        include_qualification=True,
        query_hint=inbound_message or None,
    )

    tools = make_tools(session, execution_instance)

    return LlmAgent(
        name="leadpilot_agent",
        model=settings.GEMINI_MODEL,
        instruction=compiled.system_instruction,
        tools=tools,
    )
