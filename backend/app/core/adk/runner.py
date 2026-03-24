"""
ADK runner — replaces execute_instance() from domain/runtime.py (Mission M-A).

run_for_contact() is the new entry point called from workers/tasks.py.
"""
import logging
from uuid import UUID

from google.adk.runners import Runner
from google.adk.events import Event
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.adk.agents.orchestrator import build_orchestrator
from app.core.adk.session_service import LeadPilotSessionService
from app.core.db import engine
from app.models.models import (
    ExecutionInstance,
    ExecutionStatus,
    ExecutionStepLog,
    FlowVersion,
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
        # Load ADK pipeline config from the published FlowVersion
        flow_version = await session.get(FlowVersion, execution_instance.flow_version_id)
        pipeline_config = (flow_version.adk_pipeline_config or {}) if flow_version else {}

        agent = await build_orchestrator(
            workspace_id=workspace_id,
            contact_id=contact_id,
            conversation_id=conversation_id,
            session=session,
            instance=execution_instance,
            pipeline_config=pipeline_config,
        )

        session_service = LeadPilotSessionService(db_engine=engine)
        adk_session_id = str(conversation_id)
        user_id = str(contact_id)

        existing = await session_service.get_session(
            app_name=_APP_NAME,
            user_id=user_id,
            session_id=adk_session_id,
        )

        if existing:
            adk_session = existing
        else:
            initial_state = {
                "qualification_progress": {
                    "answered_questions": [],
                    "answers": {},
                    "status": "not_started",
                    "qualified_at": None,
                    "disqualified_reason": None,
                },
                "crm_sync": {
                    "synced": False,
                    "zoho_lead_id": None,
                    "last_sync_at": None,
                    "sync_count": 0,
                },
                "conversation_intent": None,
                "escalation_requested": False,
                "lead_score": None,
                "score_updated_at": None,
            }
            adk_session = await session_service.create_session(
                app_name=_APP_NAME,
                user_id=user_id,
                session_id=adk_session_id,
                state=initial_state,
            )
            # One-time seed from last 20 DB messages (handles pre-M-C conversations)
            history_events = await _build_adk_history(conversation_id, session, limit=20)
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

        # Persist updated session (events + state) to DB
        await session_service.update_session(adk_session)

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
    limit: int = 15,
) -> list[Event]:
    """
    Load the last N messages from the DB and convert them to ADK Event objects
    for seeding into a new session. Called once on new session creation only.
    """
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # chronological order

    events: list[Event] = []
    for msg in messages:
        role = "user" if msg.direction == "inbound" else "model"
        author = "user" if msg.direction == "inbound" else "orchestrator"
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
