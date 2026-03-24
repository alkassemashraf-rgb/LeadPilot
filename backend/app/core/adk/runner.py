"""
ADK runner — replaces execute_instance() from domain/runtime.py (Mission M-A).

run_for_contact() is the new entry point called from workers/tasks.py.
"""
import logging
from uuid import UUID

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.events import Event
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.adk.agent import build_leadpilot_agent
from app.models.models import (
    ExecutionInstance,
    ExecutionStatus,
    ExecutionStepLog,
    Message,
)
from app.services.runtime_event_service import log_event

logger = logging.getLogger(__name__)

_APP_NAME = "leadpilot"


async def run_for_contact(
    workspace_id: UUID,
    contact_id: UUID,
    conversation_id: UUID,
    inbound_message: str,
    execution_instance: ExecutionInstance,
    session: AsyncSession,
) -> None:
    """
    Run the ADK agent for one inbound message turn.

    Builds the LlmAgent, seeds conversation history, runs the agent
    to completion, logs all tool calls as ExecutionStepLog rows, and
    marks the ExecutionInstance COMPLETED or FAILED.
    """
    try:
        agent = await build_leadpilot_agent(
            workspace_id, session, execution_instance, inbound_message
        )

        session_service = InMemorySessionService()
        adk_session_id = str(conversation_id)
        user_id = str(contact_id)

        adk_session = await session_service.create_session(
            app_name=_APP_NAME,
            user_id=user_id,
            session_id=adk_session_id,
        )

        # Seed conversation history from DB
        history_events = await _build_adk_history(conversation_id, session)
        for event in history_events:
            await session_service.append_event(adk_session, event)

        runner = Runner(
            agent=agent,
            app_name=_APP_NAME,
            session_service=session_service,
        )

        user_content = types.Content(
            role="user",
            parts=[types.Part(text=inbound_message)],
        )

        await log_event(
            session,
            event_type="runtime.adk_turn_started",
            source="adk_runner",
            workspace_id=workspace_id,
            related_ids={
                "execution_instance_id": str(execution_instance.id),
                "contact_id": str(contact_id),
                "conversation_id": str(conversation_id),
            },
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=adk_session_id,
            new_message=user_content,
        ):
            function_calls = event.get_function_calls()
            if function_calls:
                for call in function_calls:
                    await _log_tool_call(session, execution_instance, call)

        execution_instance.status = ExecutionStatus.COMPLETED
        session.add(execution_instance)
        await session.commit()

        await log_event(
            session,
            event_type="runtime.adk_turn_completed",
            source="adk_runner",
            workspace_id=workspace_id,
            related_ids={
                "execution_instance_id": str(execution_instance.id),
            },
        )

    except Exception as e:
        logger.exception(
            f"ADK runner failed for instance {execution_instance.id}: {e}"
        )
        execution_instance.status = ExecutionStatus.FAILED
        session.add(execution_instance)
        await session.commit()
        raise


async def _build_adk_history(
    conversation_id: UUID,
    session: AsyncSession,
) -> list[Event]:
    """
    Load the last 15 messages from the DB and convert them to ADK Event objects
    so conversation history can be seeded into the InMemorySessionService.
    """
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(15)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # chronological order

    events: list[Event] = []
    for msg in messages:
        role = "user" if msg.direction == "inbound" else "model"
        author = "user" if msg.direction == "inbound" else "leadpilot_agent"
        event = Event(
            invocation_id=f"history-{msg.id}",
            author=author,
            content=types.Content(
                role=role,
                parts=[types.Part(text=msg.content or "")],
            ),
        )
        events.append(event)

    return events


async def _log_tool_call(
    session: AsyncSession,
    instance: ExecutionInstance,
    call: types.FunctionCall,
) -> None:
    """Write one ExecutionStepLog row for an ADK tool invocation."""
    step_log = ExecutionStepLog(
        execution_instance_id=instance.id,
        node_id=None,
        input_data=dict(call.args) if call.args else {},
        output_data={"tool": call.name},
    )
    session.add(step_log)
    await session.flush()

    await log_event(
        session,
        event_type="runtime.step_completed",
        source="adk_runner",
        workspace_id=instance.workspace_id,
        related_ids={"execution_instance_id": str(instance.id)},
        payload={"tool": call.name, "args": dict(call.args) if call.args else {}},
    )
