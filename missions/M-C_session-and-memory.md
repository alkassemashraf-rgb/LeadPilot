# Mission M-C — Session & Memory

## Goal
Replace `InMemorySessionService` (used in M-A/M-B) with a persistent, DB-backed ADK
session service. ADK sessions map 1:1 to LeadPilot `Conversation` rows. Agent state
(qualification progress, conversation intent, CRM sync status) survives across webhook
events — a lead can pause mid-qualification, return 3 days later, and the agent
resumes exactly where they left off without asking repeated questions.

## What This Unlocks
- Stateful multi-turn conversations across separate webhook invocations
- Lead qualification progress survives server restarts
- Agents access historical context without rebuilding from message history every turn
- Foundation for "pause and resume" flows (WAIT_DELAY node in M-D)
- Per-lead agent memory — remember preferences, objections, previous answers

## Prerequisites
- Missions M-A and M-B complete
- `InMemorySessionService` running correctly in M-A/M-B
- ADK session state schema defined (from M-B)

---

## The Core Problem

In M-A/M-B, every webhook spins up a fresh `InMemorySessionService`. This means:
- Agent state is lost between webhook events
- History is rebuilt from DB on every turn (slow, lossy)
- No true "conversation memory" — each turn the agent starts fresh
- WAIT_DELAY nodes (M-D) are impossible without persisted state

What we need: an ADK `SessionService` backed by a new `AgentSession` table that stores
the full ADK session object (state dict + event history) per conversation.

---

## Architecture

```
Inbound webhook
  ↓
run_for_contact()
  ↓
LeadPilotSessionService.get_session(session_id=str(conversation_id))
  ↓
  ├─ session exists in DB → load and resume
  └─ no session → create new ADK session with seeded history
  ↓
ADK runner executes agent turn
  ↓
LeadPilotSessionService.save_session() → persists to DB
```

---

## Files to Create

### `backend/app/core/adk/session_service.py`

Custom implementation of ADK's `BaseSessionService` interface backed by SQLite/PostgreSQL.

```python
from google.adk.sessions import BaseSessionService, Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

class LeadPilotSessionService(BaseSessionService):
    """
    ADK SessionService backed by the LeadPilot database.
    One ADK session per Conversation (session_id == str(conversation.id)).
    """

    def __init__(self, db_engine):
        self.engine = db_engine

    async def create_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str | None = None,
        state: dict | None = None,
    ) -> Session:
        """Create a new session and persist it."""
        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id or str(uuid4()),
            state=state or {},
        )
        async with AsyncSession(self.engine) as db:
            agent_session = AgentSession(
                id=UUID(session.id),
                conversation_id=UUID(session.id),  # session_id == conversation_id
                app_name=app_name,
                user_id=user_id,
                state=session.state,
                events=[],
            )
            db.add(agent_session)
            await db.commit()
        return session

    async def get_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        config=None,
    ) -> Session | None:
        """Load an existing session from DB."""
        async with AsyncSession(self.engine) as db:
            result = await db.execute(
                select(AgentSession).where(AgentSession.id == UUID(session_id))
            )
            record = result.scalars().first()
            if not record:
                return None
            return Session(
                app_name=app_name,
                user_id=user_id,
                id=session_id,
                state=record.state or {},
                events=record.events or [],
            )

    async def update_session(self, session: Session) -> None:
        """Persist updated session state after each agent turn."""
        async with AsyncSession(self.engine) as db:
            result = await db.execute(
                select(AgentSession).where(AgentSession.id == UUID(session.id))
            )
            record = result.scalars().first()
            if record:
                record.state = session.state
                record.events = [e.model_dump() for e in session.events[-50:]]  # keep last 50
                record.updated_at = datetime.utcnow()
                db.add(record)
                await db.commit()

    async def delete_session(self, app_name, user_id, session_id) -> None:
        """Soft-delete: mark session as archived, keep for audit."""
        async with AsyncSession(self.engine) as db:
            result = await db.execute(
                select(AgentSession).where(AgentSession.id == UUID(session_id))
            )
            record = result.scalars().first()
            if record:
                record.is_archived = True
                record.updated_at = datetime.utcnow()
                db.add(record)
                await db.commit()
```

---

## Files to Modify

### `backend/app/models/models.py`

Add the `AgentSession` model:

```python
class AgentSession(SQLModel, table=True):
    """
    Persistent ADK session storage. One row per Conversation.
    session_id == str(conversation.id) — they share the same UUID.
    """
    __tablename__ = "agent_session"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(index=True, foreign_key="conversation.id")
    app_name: str = Field(default="leadpilot")
    user_id: str  # str(contact.id)

    # ADK session state — qualification progress, intent, CRM sync status, etc.
    state: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Compressed ADK event history (last 50 events)
    events: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    is_archived: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### `backend/app/core/adk/runner.py`

Replace `InMemorySessionService` with `LeadPilotSessionService`:

```python
# BEFORE (M-A/M-B)
from google.adk.sessions import InMemorySessionService
session_service = InMemorySessionService()

# AFTER (M-C)
from app.core.adk.session_service import LeadPilotSessionService
from app.core.db import engine
session_service = LeadPilotSessionService(db_engine=engine)
```

Update `run_for_contact()` to use get_session / create_session pattern:

```python
async def run_for_contact(...):
    session_service = LeadPilotSessionService(db_engine=engine)
    adk_session_id = str(conversation_id)

    # Try to resume existing session
    existing = await session_service.get_session("leadpilot", str(contact_id), adk_session_id)
    if not existing:
        # New conversation — create session with initial state
        initial_state = {
            "qualification_progress": {
                "answered_questions": [],
                "status": "not_started"
            },
            "crm_sync": {"synced": False, "zoho_lead_id": None},
            "conversation_intent": None,
        }
        await session_service.create_session(
            "leadpilot", str(contact_id), adk_session_id, state=initial_state
        )

    # Remove _build_adk_history() call — history now lives in ADK session events
    # (The session_service loads events from DB, ADK reconstructs the history)

    runner = Runner(
        agent=agent,
        app_name="leadpilot",
        session_service=session_service,
    )
    ...
```

**Remove `_build_adk_history()` and `_seed_session_history()`** from runner.py.
History is now maintained in `AgentSession.events`. No more manual DB → ADK history
conversion on every turn.

---

## Session State Contract

The `state` dict in `AgentSession` follows this schema (enforced by code, not DB):

```python
SESSION_STATE_SCHEMA = {
    # Qualification tracking
    "qualification_progress": {
        "answered_questions": [],     # list of question keys answered
        "answers": {},                # {"question_key": "answer_value"}
        "status": "not_started",      # | "in_progress" | "qualified" | "disqualified"
        "qualified_at": None,         # ISO datetime string
        "disqualified_reason": None,
    },

    # CRM sync status
    "crm_sync": {
        "synced": False,
        "zoho_lead_id": None,
        "last_sync_at": None,
        "sync_count": 0,
    },

    # Conversation classification
    "conversation_intent": None,      # "qualification" | "support" | "purchase" | "complaint"
    "escalation_requested": False,

    # Lead scoring (future M-B+ feature)
    "lead_score": None,
    "score_updated_at": None,
}
```

### State Update Patterns

QualificationAgent updates state after each answer:
```python
# Inside mark_qualified() tool
session_state = context.state  # ADK provides state via tool context
session_state["qualification_progress"]["status"] = "qualified"
session_state["qualification_progress"]["qualified_at"] = datetime.utcnow().isoformat()
# ADK persists this via session_service.update_session() after the turn
```

---

## Conversation History Strategy

**Do not store full message history in `AgentSession.events`** — it grows unbounded and
the DB already has the canonical `Message` table.

Strategy:
- `AgentSession.events` stores the last 50 ADK events (tool calls, agent responses)
  for context continuity within recent turns
- On session creation, seed the initial context from the last 20 `Message` rows
  (one-time seed, then ADK maintains its own event chain)
- For very old conversations (>50 turns), rebuild context from DB on resume

```python
async def _seed_initial_context(
    session_service: LeadPilotSessionService,
    session_id: str,
    conversation_id: UUID,
    db: AsyncSession,
) -> None:
    """Called only when creating a NEW AgentSession for an existing Conversation."""
    messages = await _load_recent_messages(conversation_id, db, limit=20)
    # Convert to ADK events and inject into the session
    # This handles the case where M-A/M-B ran before M-C was deployed
    ...
```

---

## Database Changes

### New table: `agent_session`

**Alembic migration:** `alembic/versions/XXXX_add_agent_session_table.py`

```python
def upgrade():
    op.create_table(
        "agent_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversation.id"), index=True),
        sa.Column("app_name", sa.String(), nullable=False, server_default="leadpilot"),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("state", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False, server_default="{}"),
        sa.Column("events", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False, server_default="[]"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
```

---

## Admin Portal Integration

Expose session state in the admin portal for debugging:

### Backend: `GET /api/v1/admin/contacts/{contact_id}/session`
Returns the current `AgentSession` state for a contact — useful for support team to see
what stage of qualification a lead is at.

### Frontend: Contact detail page → "Agent Session" tab
Shows:
- Qualification status + answered questions
- CRM sync status
- Conversation intent
- Session event count + last updated

---

## Tests to Write

Location: `backend/tests/test_session_service.py`

### Test 1 — Create and retrieve session
```
given: no existing AgentSession for conversation_id
when: create_session() called
then: AgentSession row created in DB, retrievable by get_session()
```

### Test 2 — State persists across turns
```
given: session with state {"qualification_progress": {"status": "in_progress"}}
when: turn 1 runs → updates state to "qualified" → update_session() called
      turn 2 runs → get_session() called
then: turn 2 sees {"qualification_progress": {"status": "qualified"}}
```

### Test 3 — Qualification resumes mid-flow after restart
```
given: session with 2 of 4 questions answered (state persisted)
when: new webhook arrives (simulates server restart between turns)
then: agent continues from question 3, not from question 1
```

### Test 4 — History seeding for new session on existing conversation
```
given: Conversation with 10 existing Messages (from before M-C)
when: new AgentSession created for that conversation
then: initial context seeded from last 20 messages
```

### Test 5 — Soft delete on conversation close
```
given: active AgentSession
when: delete_session() called (on conversation close)
then: is_archived=True, row preserved for audit
```

### Test 6 — Event cap at 50
```
given: session with 60 ADK events
when: update_session() called
then: only last 50 events stored (no unbounded growth)
```

---

## Success Criteria

- [ ] `AgentSession` table created via Alembic migration
- [ ] `LeadPilotSessionService` implements full `BaseSessionService` interface
- [ ] `runner.py` uses `LeadPilotSessionService` exclusively (no `InMemorySessionService` in production)
- [ ] Session state survives simulated restart between two webhook events
- [ ] Qualification progress resumes correctly mid-flow
- [ ] `InMemorySessionService` still used in tests (fast, isolated)
- [ ] Admin endpoint returning session state for a contact
- [ ] All M-A, M-B tests still pass
- [ ] All new M-C tests pass (6 new tests)

---

## How to Verify End-to-End

1. Send webhook 1: "Hi, I'm interested" → QualificationAgent asks question 1
2. **Stop and restart the backend**
3. Send webhook 2: answer to question 1 → agent asks question 2 (not question 1 again)
4. Query `SELECT state FROM agent_session WHERE conversation_id = '...'` → verify answered_questions contains question 1's answer
5. Complete qualification flow → `state.qualification_progress.status = "qualified"`
6. Query admin endpoint `GET /api/v1/admin/contacts/{id}/session` → returns full state
