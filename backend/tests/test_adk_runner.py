"""
Mission M-A — ADK Core Integration Tests.

Tests the new ADK runtime path: build_leadpilot_agent(), make_tools(),
and run_for_contact().
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch, call

from sqlalchemy.ext.asyncio import AsyncSession

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
    Message,
    Integration,
    IntegrationStatus,
    ZohoLeadMapping,
)
from app.core.security import get_password_hash, encrypt_data
from app.core.adk.tools import make_tools
from app.core.adk.agent import build_leadpilot_agent
from app.core.adk.runner import run_for_contact


# ── Fixtures ──────────────────────────────────────────────────────────────


async def _setup_workspace_with_contact(db: AsyncSession):
    """Create minimal workspace + contact + conversation + execution instance."""
    user = User(
        email=f"adk_test_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("testpass"),
        full_name="ADK Test",
        is_active=True,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()

    ws = Workspace(name=f"ADK WS {uuid4().hex[:4]}")
    db.add(ws)
    await db.flush()

    db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))

    contact = Contact(
        workspace_id=ws.id,
        first_name="Test",
        last_name="Lead",
        additional_metadata={},
    )
    db.add(contact)
    await db.flush()

    identity = ChannelIdentity(
        workspace_id=ws.id,
        contact_id=contact.id,
        provider="whatsapp",
        provider_user_id="14155550000",
    )
    db.add(identity)

    conversation = Conversation(
        workspace_id=ws.id,
        contact_id=contact.id,
        status=ConversationStatus.BOT_ACTIVE,
    )
    db.add(conversation)

    flow = Flow(workspace_id=ws.id, name="Test Flow", status="published")
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


# ── Test 1: build_leadpilot_agent returns valid LlmAgent with 4 tools ─────


@pytest.mark.asyncio
async def test_build_leadpilot_agent_has_four_tools(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    compiled = MagicMock()
    compiled.system_instruction = "You are a helpful sales assistant."
    compiled.version_id = uuid4()

    with patch(
        "app.core.adk.agent.compile_workspace_prompt",
        new=AsyncMock(return_value=compiled),
    ):
        agent = await build_leadpilot_agent(
            workspace_id=ws.id,
            session=db_session,
            execution_instance=instance,
            inbound_message="Hello",
        )

    assert agent.name == "leadpilot_agent"
    assert agent.instruction == compiled.system_instruction
    # ADK stores tools as a list on the agent
    assert len(agent.tools) == 4
    tool_names = {t.name for t in agent.tools}
    assert tool_names == {"send_reply", "upsert_zoho_lead", "escalate_to_human", "tag_contact"}


# ── Test 2: send_reply tool stores Message and triggers dispatch ──────────


@pytest.mark.asyncio
async def test_send_reply_tool_stores_message_and_dispatches(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    tools = make_tools(db_session, instance)
    send_reply_fn = next(t.func for t in tools if t.name == "send_reply")

    with patch("app.workers.tasks.dispatch_message_task") as mock_task:
        mock_task.delay = MagicMock()
        result = await send_reply_fn(message_content="Hi there!")

    assert result == {"status": "sent"}

    from sqlmodel import select
    msg_result = await db_session.execute(
        select(Message).where(
            Message.workspace_id == ws.id,
            Message.direction == "outbound",
        )
    )
    msg = msg_result.scalars().first()
    assert msg is not None
    assert msg.content == "Hi there!"
    assert msg.is_outbound_intent is True
    mock_task.delay.assert_called_once()


# ── Test 3: upsert_zoho_lead tool calls ZohoAdapter ──────────────────────


@pytest.mark.asyncio
async def test_upsert_zoho_lead_tool_calls_adapter(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    # Set up Zoho integration and mapping
    integration = Integration(
        workspace_id=ws.id,
        provider="zoho",
        status=IntegrationStatus.CONNECTED,
        encrypted_config='{"access_token": "tok", "refresh_token": "ref", "client_id": "cid", "client_secret": "cs"}',
    )
    db_session.add(integration)

    mapping = ZohoLeadMapping(
        workspace_id=ws.id,
        field_mappings={"Last Name": "last_name"},
        dedupe_strategy="email",
    )
    db_session.add(mapping)
    await db_session.flush()

    tools = make_tools(db_session, instance)
    upsert_fn = next(t.func for t in tools if t.name == "upsert_zoho_lead")

    with (
        patch("app.services.zoho_payload_builder.build_zoho_payload", new=AsyncMock(return_value={"Last Name": "Lead"})),
        patch("app.integrations.zoho.adapter.ZohoAdapter.upsert_lead", new=AsyncMock(return_value=("ZL-001", "create"))),
    ):
        result = await upsert_fn()

    assert result["action"] in ("create", "update")
    assert result["zoho_lead_id"] == "ZL-001"


# ── Test 4: escalate_to_human sets Conversation.HUMAN_TAKEOVER ───────────


@pytest.mark.asyncio
async def test_escalate_to_human_sets_status(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    tools = make_tools(db_session, instance)
    escalate_fn = next(t.func for t in tools if t.name == "escalate_to_human")

    with patch("app.workers.tasks.dispatch_message_task") as mock_task:
        mock_task.delay = MagicMock()
        result = await escalate_fn(announcement_message="Connecting you to an agent now.")

    assert result == {"status": "escalated"}

    await db_session.refresh(conversation)
    assert conversation.status == ConversationStatus.HUMAN_TAKEOVER


# ── Test 5: run_for_contact marks instance COMPLETED ─────────────────────


@pytest.mark.asyncio
async def test_run_for_contact_marks_completed(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    compiled = MagicMock()
    compiled.system_instruction = "You are a sales bot."
    compiled.version_id = uuid4()

    # Mock ADK event with no tool calls and is_final_response = True
    mock_event = MagicMock()
    mock_event.get_function_calls.return_value = []
    mock_event.is_final_response.return_value = True

    async def _fake_run_async(**kwargs):
        yield mock_event

    mock_svc = MagicMock()
    mock_svc.get_session = AsyncMock(return_value=None)
    mock_svc.create_session = AsyncMock(return_value=MagicMock())
    mock_svc.append_event = AsyncMock()
    mock_svc.update_session = AsyncMock()

    with (
        patch("app.core.adk.agent.compile_workspace_prompt", new=AsyncMock(return_value=compiled)),
        patch("google.adk.runners.Runner.run_async", side_effect=_fake_run_async),
        patch("app.core.adk.runner.LeadPilotSessionService", return_value=mock_svc),
    ):
        await run_for_contact(
            workspace_id=ws.id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            inbound_message="Hello",
            execution_instance=instance,
            session=db_session,
        )

    await db_session.refresh(instance)
    assert instance.status == ExecutionStatus.COMPLETED


# ── Test 6: run_for_contact marks instance FAILED on exception ────────────


@pytest.mark.asyncio
async def test_run_for_contact_marks_failed_on_error(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    compiled = MagicMock()
    compiled.system_instruction = "You are a sales bot."
    compiled.version_id = uuid4()

    async def _fake_run_async(**kwargs):
        raise RuntimeError("Gemini API unavailable")
        yield  # make it an async generator

    mock_svc = MagicMock()
    mock_svc.get_session = AsyncMock(return_value=None)
    mock_svc.create_session = AsyncMock(return_value=MagicMock())
    mock_svc.append_event = AsyncMock()
    mock_svc.update_session = AsyncMock()

    with (
        patch("app.core.adk.agent.compile_workspace_prompt", new=AsyncMock(return_value=compiled)),
        patch("google.adk.runners.Runner.run_async", side_effect=_fake_run_async),
        patch("app.core.adk.runner.LeadPilotSessionService", return_value=mock_svc),
    ):
        with pytest.raises(RuntimeError, match="Gemini API unavailable"):
            await run_for_contact(
                workspace_id=ws.id,
                contact_id=contact.id,
                conversation_id=conversation.id,
                inbound_message="Hello",
                execution_instance=instance,
                session=db_session,
            )

    await db_session.refresh(instance)
    assert instance.status == ExecutionStatus.FAILED
