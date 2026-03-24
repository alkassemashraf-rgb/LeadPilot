"""
Mission M-B — Multi-Agent Orchestration Tests.

Tests the 5-agent hierarchy: build_orchestrator(), sub-agent builders,
and the qualification tools (mark_qualified, mark_disqualified).
"""
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

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
    Flow,
    FlowVersion,
)
from app.core.security import get_password_hash
from app.core.adk.agents.orchestrator import build_orchestrator
from app.core.adk.agents.qualification import build_qualification_agent


# ── Fixtures ──────────────────────────────────────────────────────────────


async def _setup_workspace_with_contact(
    db: AsyncSession,
    qualification_status: str | None = None,
    zoho_lead_id: str | None = None,
) -> tuple:
    """Create minimal workspace + contact + conversation + execution instance."""
    user = User(
        email=f"mb_test_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("testpass"),
        full_name="MB Test",
        is_active=True,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()

    ws = Workspace(name=f"MB WS {uuid4().hex[:4]}")
    db.add(ws)
    await db.flush()

    db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))

    contact = Contact(
        workspace_id=ws.id,
        first_name="Test",
        last_name="Lead",
        additional_metadata={},
        qualification_status=qualification_status,
        zoho_lead_id=zoho_lead_id,
    )
    db.add(contact)
    await db.flush()

    identity = ChannelIdentity(
        workspace_id=ws.id,
        contact_id=contact.id,
        provider="whatsapp",
        provider_user_id="14155550001",
    )
    db.add(identity)

    conversation = Conversation(
        workspace_id=ws.id,
        contact_id=contact.id,
        status=ConversationStatus.BOT_ACTIVE,
    )
    db.add(conversation)

    flow = Flow(workspace_id=ws.id, name="MB Test Flow", status="published")
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


# ── Test 1: build_orchestrator produces agent with 4 AgentTools ───────────


@pytest.mark.asyncio
async def test_build_orchestrator_has_four_agent_tools(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)

    compiled = MagicMock()
    compiled.system_instruction = "You are a helpful sales assistant."

    with patch(
        "app.core.adk.agents.orchestrator.compile_workspace_prompt",
        new=AsyncMock(return_value=compiled),
    ):
        agent = await build_orchestrator(
            workspace_id=ws.id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            session=db_session,
            instance=instance,
        )

    assert agent.name == "orchestrator"
    assert len(agent.tools) == 4
    tool_names = {t.agent.name for t in agent.tools}
    assert tool_names == {"qualification_agent", "crm_agent", "reply_agent", "handover_agent"}


# ── Test 2: Instruction reflects unqualified + CRM-unsynced state ─────────


@pytest.mark.asyncio
async def test_orchestrator_instruction_unqualified_state(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(
        db_session,
        qualification_status=None,
        zoho_lead_id=None,
    )

    compiled = MagicMock()
    compiled.system_instruction = "Business context."

    with patch(
        "app.core.adk.agents.orchestrator.compile_workspace_prompt",
        new=AsyncMock(return_value=compiled),
    ):
        agent = await build_orchestrator(
            workspace_id=ws.id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            session=db_session,
            instance=instance,
        )

    assert "not yet qualified" in agent.instruction
    assert "no" in agent.instruction  # CRM synced: no


# ── Test 3: Instruction reflects qualified + CRM-synced state ─────────────


@pytest.mark.asyncio
async def test_orchestrator_instruction_qualified_synced_state(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(
        db_session,
        qualification_status="qualified",
        zoho_lead_id="ZL-999",
    )

    compiled = MagicMock()
    compiled.system_instruction = "Business context."

    with patch(
        "app.core.adk.agents.orchestrator.compile_workspace_prompt",
        new=AsyncMock(return_value=compiled),
    ):
        agent = await build_orchestrator(
            workspace_id=ws.id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            session=db_session,
            instance=instance,
        )

    # Both "qualified" and "yes" should appear in the routing context section
    assert "qualified" in agent.instruction
    assert "yes" in agent.instruction  # CRM synced: yes


# ── Test 4: mark_qualified tool updates Contact.qualification_status ───────


@pytest.mark.asyncio
async def test_mark_qualified_updates_contact(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)
    assert contact.qualification_status is None

    agent = build_qualification_agent(
        qualification_questions=[{"label": "What is your budget?", "enabled": True, "order": 0}],
        qualification_criteria=[{"label": "Budget > $1000", "is_enabled": True, "sort_order": 0}],
        session=db_session,
        instance=instance,
    )

    # Locate the mark_qualified FunctionTool and invoke its inner function directly
    mark_qualified_tool = next(t for t in agent.tools if t.name == "mark_qualified")
    result = await mark_qualified_tool.func(reason="Budget confirmed at $5000")

    assert result["qualification_status"] == "qualified"

    await db_session.refresh(contact)
    assert contact.qualification_status == "qualified"
    assert "qualified" in (contact.additional_metadata or {}).get("tags", [])


# ── Test 5: mark_disqualified tool updates Contact.qualification_status ────


@pytest.mark.asyncio
async def test_mark_disqualified_updates_contact(db_session: AsyncSession):
    ws, contact, conversation, instance = await _setup_workspace_with_contact(db_session)
    assert contact.qualification_status is None

    agent = build_qualification_agent(
        qualification_questions=[],
        qualification_criteria=[],
        session=db_session,
        instance=instance,
    )

    mark_disqualified_tool = next(t for t in agent.tools if t.name == "mark_disqualified")
    result = await mark_disqualified_tool.func(reason="Budget too low")

    assert result["qualification_status"] == "disqualified"

    await db_session.refresh(contact)
    assert contact.qualification_status == "disqualified"
    assert "disqualified" in (contact.additional_metadata or {}).get("tags", [])
