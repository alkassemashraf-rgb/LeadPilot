"""
Mission M-E — End-to-End Agent Flow Tests.

Tests the ADK execution path end-to-end: inbound message → runner →
tool calls → event logging → status transitions. Uses mocked Runner to
avoid real Gemini API calls.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.adk.runner import run_for_contact
from app.models.models import (
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    Contact,
    ChannelIdentity,
    Conversation,
    ConversationStatus,
    ExecutionInstance,
    ExecutionStatus,
    ExecutionStepLog,
    Flow,
    FlowVersion,
    RuntimeEventLog,
)
from app.core.security import get_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────


async def _setup_workspace_with_contact(db: AsyncSession):
    """Create minimal workspace + contact + conversation + execution instance."""
    user = User(
        email=f"e2e_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("pass"),
        full_name="E2E Test",
        is_active=True,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()

    ws = Workspace(name=f"E2E WS {uuid4().hex[:4]}")
    db.add(ws)
    await db.flush()

    db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))

    contact = Contact(
        workspace_id=ws.id,
        first_name="E2E",
        last_name="Lead",
        additional_metadata={},
    )
    db.add(contact)
    await db.flush()

    db.add(ChannelIdentity(
        workspace_id=ws.id,
        contact_id=contact.id,
        provider="whatsapp",
        provider_user_id=f"e2e_{uuid4().hex[:6]}",
    ))

    conversation = Conversation(
        workspace_id=ws.id,
        contact_id=contact.id,
        status=ConversationStatus.BOT_ACTIVE,
    )
    db.add(conversation)

    flow = Flow(workspace_id=ws.id, name="E2E Flow", status="published")
    db.add(flow)
    await db.flush()

    flow_version = FlowVersion(
        workspace_id=ws.id,
        flow_id=flow.id,
        version_number=1,
        is_published=True,
        definition_json={"nodes": [], "edges": []},
    )
    db.add(flow_version)
    await db.flush()

    instance = ExecutionInstance(
        workspace_id=ws.id,
        flow_version_id=flow_version.id,
        contact_id=contact.id,
        status=ExecutionStatus.RUNNING,
    )
    db.add(instance)
    await db.flush()

    return ws, contact, conversation, instance


def _compiled_prompt():
    c = MagicMock()
    c.system_instruction = "You are a helpful sales assistant."
    c.version_id = uuid4()
    return c


# ── E2E Test 1: tool call produces step log + runtime events ──────────────


@pytest.mark.asyncio
async def test_run_for_contact_tool_call_produces_step_log_and_events(
    db_session: AsyncSession,
):
    """
    When the runner emits a tool-call event, _log_tool_call() writes an
    ExecutionStepLog row and a RuntimeEventLog entry.
    """
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    fake_call = MagicMock()
    fake_call.name = "send_reply"
    fake_call.args = {"message_content": "Hello there!"}

    mock_event = MagicMock()
    mock_event.get_function_calls.return_value = [fake_call]

    async def _fake_run_async(**kwargs):
        yield mock_event

    mock_svc = MagicMock()
    mock_svc.get_session = AsyncMock(return_value=None)
    mock_svc.create_session = AsyncMock(return_value=MagicMock())
    mock_svc.append_event = AsyncMock()
    mock_svc.update_session = AsyncMock()

    with (
        patch(
            "app.core.adk.agents.orchestrator.compile_workspace_prompt",
            new=AsyncMock(return_value=_compiled_prompt()),
        ),
        patch("google.adk.runners.Runner.run_async", side_effect=_fake_run_async),
        patch("app.core.adk.runner.LeadPilotSessionService", return_value=mock_svc),
    ):
        await run_for_contact(
            workspace_id=ws.id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            inbound_message="Hi",
            execution_instance=instance,
            session=db_session,
        )

    # ExecutionStepLog written for the tool call
    step_result = await db_session.execute(
        select(ExecutionStepLog).where(
            ExecutionStepLog.execution_instance_id == instance.id
        )
    )
    step_log = step_result.scalars().first()
    assert step_log is not None
    assert step_log.output_data == {"tool": "send_reply"}

    # RuntimeEventLog has adk_turn_started + step_completed + adk_turn_completed
    event_result = await db_session.execute(
        select(RuntimeEventLog).where(
            RuntimeEventLog.related_ids["execution_instance_id"].as_string()
            == str(instance.id)
        )
    )
    events = event_result.scalars().all()
    event_types = {e.event_type for e in events}
    assert "runtime.adk_turn_started" in event_types
    assert "runtime.step_completed" in event_types
    assert "runtime.adk_turn_completed" in event_types

    # Instance completed
    await db_session.refresh(instance)
    assert instance.status == ExecutionStatus.COMPLETED


# ── E2E Test 2: exception marks instance FAILED ───────────────────────────


@pytest.mark.asyncio
async def test_run_for_contact_exception_marks_instance_failed(
    db_session: AsyncSession,
):
    """
    When the ADK runner raises, the ExecutionInstance is marked FAILED
    and the exception is re-raised.
    """
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    async def _raise_on_run(**kwargs):
        raise RuntimeError("Gemini API unavailable")
        yield  # pragma: no cover

    mock_svc = MagicMock()
    mock_svc.get_session = AsyncMock(return_value=None)
    mock_svc.create_session = AsyncMock(return_value=MagicMock())
    mock_svc.append_event = AsyncMock()
    mock_svc.update_session = AsyncMock()

    with (
        patch(
            "app.core.adk.agents.orchestrator.compile_workspace_prompt",
            new=AsyncMock(return_value=_compiled_prompt()),
        ),
        patch("google.adk.runners.Runner.run_async", side_effect=_raise_on_run),
        patch("app.core.adk.runner.LeadPilotSessionService", return_value=mock_svc),
    ):
        with pytest.raises(RuntimeError, match="Gemini API unavailable"):
            await run_for_contact(
                workspace_id=ws.id,
                contact_id=contact.id,
                conversation_id=conversation.id,
                inbound_message="Hi",
                execution_instance=instance,
                session=db_session,
            )

    await db_session.refresh(instance)
    assert instance.status == ExecutionStatus.FAILED


# ── E2E Test 3: WAIT_DELAY resume cycle ───────────────────────────────────


@pytest.mark.asyncio
async def test_wait_delay_instance_resumes_and_completes(db_session: AsyncSession):
    """
    Simulate the WAIT_DELAY resume cycle:
      WAITING (resume_at elapsed) → mark RUNNING → run_for_contact → COMPLETED.

    This mirrors what resume_waiting_instances_task does, tested directly
    against run_for_contact to avoid Celery engine-session isolation issues.
    """
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    # Put instance in WAITING state with an already-elapsed resume_at
    instance.status = ExecutionStatus.WAITING
    instance.resume_at = datetime.utcnow() - timedelta(minutes=5)
    db_session.add(instance)
    await db_session.flush()

    # Simulate the task's "mark RUNNING before calling run_for_contact"
    instance.status = ExecutionStatus.RUNNING
    db_session.add(instance)
    await db_session.flush()

    mock_event = MagicMock()
    mock_event.get_function_calls.return_value = []

    async def _fake_run_async(**kwargs):
        yield mock_event

    mock_svc = MagicMock()
    mock_svc.get_session = AsyncMock(return_value=None)
    mock_svc.create_session = AsyncMock(return_value=MagicMock())
    mock_svc.append_event = AsyncMock()
    mock_svc.update_session = AsyncMock()

    with (
        patch(
            "app.core.adk.agents.orchestrator.compile_workspace_prompt",
            new=AsyncMock(return_value=_compiled_prompt()),
        ),
        patch("google.adk.runners.Runner.run_async", side_effect=_fake_run_async),
        patch("app.core.adk.runner.LeadPilotSessionService", return_value=mock_svc),
    ):
        await run_for_contact(
            workspace_id=ws.id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            inbound_message="[Resumed after delay]",
            execution_instance=instance,
            session=db_session,
        )

    await db_session.refresh(instance)
    assert instance.status == ExecutionStatus.COMPLETED
