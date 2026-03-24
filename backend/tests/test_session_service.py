"""
Mission M-C — LeadPilotSessionService Tests.

Tests the DB-backed ADK session service: create, get, update, delete,
event capping, and history seeding.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from google.adk.events import Event
from google.genai import types

from uuid import UUID

from app.core.adk.session_service import LeadPilotSessionService
from app.models.models import (
    AgentSession,
    Conversation,
    ConversationStatus,
    Contact,
    Message,
    Workspace,
)

# Import the test engine so the service can open its own DB sessions
# (conftest.engine uses test.db — the same file the session fixture uses)
from conftest import engine as test_engine


def _make_event(text: str, author: str = "user") -> Event:
    """Build a minimal ADK Event for testing."""
    return Event(
        invocation_id=f"inv-{uuid4().hex[:8]}",
        author=author,
        content=types.Content(
            role="user" if author == "user" else "model",
            parts=[types.Part(text=text)],
        ),
    )


# ── Test 1: Create and retrieve session ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_retrieve_session():
    """create_session() → get_session() returns same state."""
    svc = LeadPilotSessionService(db_engine=test_engine)
    conversation_id = str(uuid4())
    contact_id = str(uuid4())
    initial_state = {"qualification_progress": {"status": "not_started"}}

    created = await svc.create_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
        state=initial_state,
    )
    assert created.id == conversation_id
    assert created.state["qualification_progress"]["status"] == "not_started"

    # Fresh service instance (simulates a new request — no cache)
    svc2 = LeadPilotSessionService(db_engine=test_engine)
    loaded = await svc2.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    assert loaded is not None
    assert loaded.id == conversation_id
    assert loaded.state["qualification_progress"]["status"] == "not_started"


# ── Test 2: State persists across turns ──────────────────────────────────────


@pytest.mark.asyncio
async def test_state_persists_across_turns():
    """update_session with new state → next get_session returns updated state."""
    svc = LeadPilotSessionService(db_engine=test_engine)
    conversation_id = str(uuid4())
    contact_id = str(uuid4())

    await svc.create_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
        state={"qualification_progress": {"status": "in_progress"}},
    )

    # Simulate turn 1: agent marks qualified
    session = await svc.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    session.state["qualification_progress"]["status"] = "qualified"
    session.state["qualification_progress"]["qualified_at"] = datetime.utcnow().isoformat()
    await svc.update_session(session)

    # Turn 2: new service instance (no cache) — should see "qualified"
    svc2 = LeadPilotSessionService(db_engine=test_engine)
    resumed = await svc2.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    assert resumed is not None
    assert resumed.state["qualification_progress"]["status"] == "qualified"
    assert resumed.state["qualification_progress"]["qualified_at"] is not None


# ── Test 3: Qualification resumes mid-flow after restart ─────────────────────


@pytest.mark.asyncio
async def test_qualification_resumes_mid_flow():
    """Session with partial progress survives a simulated server restart."""
    conversation_id = str(uuid4())
    contact_id = str(uuid4())

    # Turn 1: answer question 1
    svc1 = LeadPilotSessionService(db_engine=test_engine)
    await svc1.create_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
        state={
            "qualification_progress": {
                "answered_questions": [],
                "answers": {},
                "status": "in_progress",
            }
        },
    )
    session = await svc1.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    session.state["qualification_progress"]["answered_questions"] = ["q1"]
    session.state["qualification_progress"]["answers"]["q1"] = "Yes, I'm interested"
    await svc1.update_session(session)

    # Simulate restart: brand-new service instance
    svc2 = LeadPilotSessionService(db_engine=test_engine)
    resumed = await svc2.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    assert resumed is not None
    assert "q1" in resumed.state["qualification_progress"]["answered_questions"]
    assert resumed.state["qualification_progress"]["answers"]["q1"] == "Yes, I'm interested"
    assert resumed.state["qualification_progress"]["status"] == "in_progress"


# ── Test 4: History seeding for new session on existing conversation ──────────


@pytest.mark.asyncio
async def test_history_seeding_for_new_session():
    """
    New AgentSession seeded from last N DB Messages has events populated.
    Uses test_engine directly (committed transactions) so Messages are visible
    to the service's internal sessions.
    """
    from sqlalchemy.ext.asyncio import AsyncSession as AsyncDbSession
    from sqlmodel import select
    from app.core.adk.runner import _build_adk_history

    # Create all setup data via test_engine with committed transactions
    # so they're visible to the service's own sessions (cross-connection)
    async with AsyncDbSession(test_engine) as db:
        ws = Workspace(name=f"MC Test WS {uuid4().hex[:4]}")
        db.add(ws)
        await db.flush()

        contact = Contact(workspace_id=ws.id, first_name="Test", additional_metadata={})
        db.add(contact)
        await db.flush()

        conversation = Conversation(
            workspace_id=ws.id,
            contact_id=contact.id,
            status=ConversationStatus.BOT_ACTIVE,
        )
        db.add(conversation)
        await db.flush()

        for i in range(10):
            msg = Message(
                workspace_id=ws.id,
                conversation_id=conversation.id,
                contact_id=contact.id,
                direction="inbound" if i % 2 == 0 else "outbound",
                content=f"Message {i}",
                channel="whatsapp",
                platform="whatsapp",
            )
            db.add(msg)
        await db.flush()
        # Capture IDs before commit (after commit, expire_on_commit=True would
        # expire attributes and accessing them outside greenlet raises MissingGreenlet)
        conversation_id = str(conversation.id)
        contact_id = str(contact.id)
        await db.commit()

    # Seed a new ADK session from DB history
    svc = LeadPilotSessionService(db_engine=test_engine)
    adk_session = await svc.create_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
        state={},
    )

    async with AsyncDbSession(test_engine) as db:
        history_events = await _build_adk_history(UUID(conversation_id), db, limit=10)
    for event in history_events:
        await svc.append_event(adk_session, event)

    assert len(adk_session.events) == 10

    # Persist and reload to confirm events survive serialization round-trip
    await svc.update_session(adk_session)
    svc2 = LeadPilotSessionService(db_engine=test_engine)
    reloaded = await svc2.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    assert reloaded is not None
    assert len(reloaded.events) == 10


# ── Test 5: Soft delete on conversation close ─────────────────────────────────


@pytest.mark.asyncio
async def test_soft_delete_on_close():
    """delete_session() marks is_archived=True, row preserved for audit."""
    svc = LeadPilotSessionService(db_engine=test_engine)
    conversation_id = str(uuid4())
    contact_id = str(uuid4())

    await svc.create_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
        state={},
    )

    # Confirm session exists
    loaded = await svc.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    assert loaded is not None

    await svc.delete_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )

    # get_session after delete returns None (is_archived filter)
    svc2 = LeadPilotSessionService(db_engine=test_engine)
    deleted = await svc2.get_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
    )
    assert deleted is None

    # Row still exists in DB with is_archived=True
    from sqlalchemy.ext.asyncio import AsyncSession as AsyncDbSession
    from sqlmodel import select
    async with AsyncDbSession(test_engine) as db:
        result = await db.execute(
            select(AgentSession).where(AgentSession.id == UUID(conversation_id))
        )
        record = result.scalars().first()
    assert record is not None
    assert record.is_archived is True


# ── Test 6: Event cap at 50 ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_event_cap_at_50():
    """update_session() stores only the last 50 events (no unbounded growth)."""
    svc = LeadPilotSessionService(db_engine=test_engine)
    conversation_id = str(uuid4())
    contact_id = str(uuid4())

    session = await svc.create_session(
        app_name="leadpilot",
        user_id=contact_id,
        session_id=conversation_id,
        state={},
    )

    # Append 60 events
    for i in range(60):
        event = _make_event(f"Message {i}", author="user" if i % 2 == 0 else "orchestrator")
        await svc.append_event(session, event)

    assert len(session.events) == 60  # in-memory has all 60

    await svc.update_session(session)

    # DB should store only the last 50
    from sqlalchemy.ext.asyncio import AsyncSession as AsyncDbSession
    from sqlmodel import select
    async with AsyncDbSession(test_engine) as db:
        result = await db.execute(
            select(AgentSession).where(AgentSession.id == UUID(conversation_id))
        )
        record = result.scalars().first()
    assert record is not None
    assert len(record.events) == 50
