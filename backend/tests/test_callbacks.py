"""
Mission M-E — Callback Integration Tests.

Tests LeadPilotCallbackHandler (log_event wiring) and the admin
execution trace endpoint.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.adk.callbacks import LeadPilotCallbackHandler, _redact_sensitive
from app.core.security import get_password_hash, create_access_token
from app.models.models import (
    RuntimeEventLog,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_handler(db: AsyncSession, workspace_id=None, instance_id=None):
    ws_id = str(workspace_id or uuid4())
    inst_id = str(instance_id or uuid4())
    return LeadPilotCallbackHandler(
        workspace_id=ws_id,
        instance_id=inst_id,
        db_session=db,
    ), ws_id, inst_id


def _mock_callback_context(agent_name: str = "orchestrator"):
    ctx = MagicMock()
    ctx.agent_name = agent_name
    return ctx


# ── Test 1: before_agent logs agent.started event ─────────────────────────


@pytest.mark.asyncio
async def test_before_agent_logs_started_event(db_session: AsyncSession):
    handler, ws_id, inst_id = _make_handler(db_session)
    ctx = _mock_callback_context("orchestrator")

    await handler.before_agent(callback_context=ctx)
    await db_session.flush()

    result = await db_session.execute(
        select(RuntimeEventLog).where(
            RuntimeEventLog.event_type == "agent.orchestrator.started"
        )
    )
    event = result.scalars().first()
    assert event is not None
    assert event.source == "adk"
    assert event.related_ids["execution_instance_id"] == inst_id
    assert event.payload["agent_name"] == "orchestrator"


# ── Test 2: after_tool logs tool.completed event ──────────────────────────


@pytest.mark.asyncio
async def test_after_tool_logs_completed_event(db_session: AsyncSession):
    handler, ws_id, inst_id = _make_handler(db_session)

    tool = MagicMock()
    tool.name = "send_reply"
    args = {"message_content": "Hello!"}
    tool_response = {"status": "sent"}

    await handler.after_tool(
        tool=tool, args=args, tool_context=MagicMock(), tool_response=tool_response
    )
    await db_session.flush()

    result = await db_session.execute(
        select(RuntimeEventLog).where(
            RuntimeEventLog.event_type == "tool.send_reply.completed"
        )
    )
    event = result.scalars().first()
    assert event is not None
    assert event.source == "adk"
    assert event.payload["tool_name"] == "send_reply"
    assert event.payload["result_fields"] == ["status"]


# ── Test 3: on_model_error logs failure outcome ───────────────────────────


@pytest.mark.asyncio
async def test_on_model_error_logs_failure_outcome(db_session: AsyncSession):
    handler, ws_id, inst_id = _make_handler(db_session)
    ctx = _mock_callback_context()
    llm_request = MagicMock()
    error = RuntimeError("Gemini unavailable")

    await handler.on_model_error(
        callback_context=ctx, llm_request=llm_request, error=error
    )
    await db_session.flush()

    result = await db_session.execute(
        select(RuntimeEventLog).where(
            RuntimeEventLog.event_type == "agent.error",
            RuntimeEventLog.outcome == "failure",
        )
    )
    event = result.scalars().first()
    assert event is not None
    assert event.error_message == "Gemini unavailable"
    assert event.payload["error_type"] == "RuntimeError"
    assert event.payload["phase"] == "llm"


# ── Test 4: sensitive args are redacted ───────────────────────────────────


def test_sensitive_args_redacted():
    args = {
        "access_token": "secret123",
        "api_key": "sk-abc",
        "message": "Hello!",
        "token": "bearer-xyz",
    }
    redacted = _redact_sensitive(args)
    assert redacted["access_token"] == "***"
    assert redacted["api_key"] == "***"
    assert redacted["token"] == "***"
    assert redacted["message"] == "Hello!"


# ── Test 5: execution trace endpoint returns ordered events ───────────────


@pytest.mark.asyncio
async def test_execution_trace_endpoint_returns_ordered_events(
    db_session: AsyncSession, async_client
):
    # Create superadmin user
    admin = User(
        email=f"trace_admin_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("pass"),
        full_name="Trace Admin",
        is_active=True,
        is_superuser=True,
        email_verified_at=datetime.utcnow(),
    )
    db_session.add(admin)
    await db_session.flush()
    admin_id = admin.id
    await db_session.commit()

    token = create_access_token(admin_id)
    headers = {"Authorization": f"Bearer {token}"}

    instance_id = str(uuid4())
    ws_id = uuid4()

    # Insert 3 events in order (oldest first)
    base_time = datetime.utcnow()
    for i, etype in enumerate(
        ["runtime.adk_turn_started", "agent.orchestrator.started", "tool.send_reply.completed"]
    ):
        event = RuntimeEventLog(
            workspace_id=ws_id,
            event_type=etype,
            source="adk",
            outcome="success",
            related_ids={"execution_instance_id": instance_id},
            created_at=base_time + timedelta(seconds=i),
        )
        db_session.add(event)
    await db_session.commit()

    resp = await async_client.get(
        f"/api/v1/admin/executions/{instance_id}/trace",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    events = body["data"]["events"]
    assert len(events) == 3
    # Verify chronological order
    assert events[0]["event_type"] == "runtime.adk_turn_started"
    assert events[1]["event_type"] == "agent.orchestrator.started"
    assert events[2]["event_type"] == "tool.send_reply.completed"
