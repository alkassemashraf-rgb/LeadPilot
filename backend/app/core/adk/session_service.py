"""
LeadPilotSessionService — ADK SessionService backed by the LeadPilot database.

One AgentSession row per Conversation (session_id == str(conversation.id)).
Uses an in-memory cache per-instance so the ADK Runner always gets the same
object reference (important: append_event modifies in-place, and the Runner
calls get_session() internally — the cache ensures it receives the same
reference we hold, so updates are visible after the run loop).
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from google.adk.events import Event
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import ListSessionsResponse
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDbSession
from sqlmodel import select

from app.models.models import AgentSession

logger = logging.getLogger(__name__)


class LeadPilotSessionService(BaseSessionService):
    """
    ADK SessionService backed by the LeadPilot database.
    Instantiated once per run_for_contact() call (per-request, not shared).
    """

    def __init__(self, db_engine):
        self.engine = db_engine
        # In-memory cache: session_id -> Session object
        # Ensures the Runner receives the same reference we create/load,
        # so in-place append_event mutations are visible after the run loop.
        self._cache: dict[str, Session] = {}

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create a new session and persist it to DB."""
        sid = session_id or str(uuid4())
        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=sid,
            state=state or {},
            events=[],
        )
        async with AsyncDbSession(self.engine) as db:
            record = AgentSession(
                id=UUID(sid),
                conversation_id=UUID(sid),  # session_id == conversation_id
                app_name=app_name,
                user_id=user_id,
                state=state or {},
                events=[],
            )
            db.add(record)
            await db.commit()

        self._cache[sid] = session
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config=None,
    ) -> Optional[Session]:
        """Load an existing session. Returns cached reference if available."""
        if session_id in self._cache:
            return self._cache[session_id]

        async with AsyncDbSession(self.engine) as db:
            result = await db.execute(
                select(AgentSession).where(
                    AgentSession.id == UUID(session_id),
                    AgentSession.is_archived.is_(False),
                )
            )
            record = result.scalars().first()
            if not record:
                return None

            session = Session(
                app_name=app_name,
                user_id=user_id,
                id=session_id,
                state=record.state or {},
                events=[Event.model_validate(e) for e in (record.events or [])],
            )

        self._cache[session_id] = session
        return session

    async def update_session(self, session: Session) -> None:
        """Persist updated session state and events to DB after each agent turn."""
        async with AsyncDbSession(self.engine) as db:
            result = await db.execute(
                select(AgentSession).where(AgentSession.id == UUID(session.id))
            )
            record = result.scalars().first()
            if not record:
                logger.warning(
                    "update_session: AgentSession %s not found in DB — skipping persist",
                    session.id,
                )
                return

            # Persist state (convert State wrapper to plain dict if needed)
            raw_state = session.state
            record.state = dict(raw_state) if hasattr(raw_state, "to_dict") else raw_state

            # Cap events at last 50 to prevent unbounded growth
            record.events = [e.model_dump() for e in session.events[-50:]]
            record.updated_at = datetime.utcnow()

            db.add(record)
            await db.commit()

    async def list_sessions(
        self,
        *,
        app_name: str,
        user_id: Optional[str] = None,
    ) -> ListSessionsResponse:
        """List all active sessions for an app (and optionally a user)."""
        async with AsyncDbSession(self.engine) as db:
            query = select(AgentSession).where(
                AgentSession.app_name == app_name,
                AgentSession.is_archived.is_(False),
            )
            if user_id is not None:
                query = query.where(AgentSession.user_id == user_id)

            result = await db.execute(query)
            records = result.scalars().all()

        # Per ADK convention: events and state are NOT populated in list results
        sessions = [
            Session(
                app_name=r.app_name,
                user_id=r.user_id,
                id=str(r.id),
                state={},
                events=[],
            )
            for r in records
        ]
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        """Soft-delete: mark session as archived, keep row for audit."""
        self._cache.pop(session_id, None)

        async with AsyncDbSession(self.engine) as db:
            result = await db.execute(
                select(AgentSession).where(AgentSession.id == UUID(session_id))
            )
            record = result.scalars().first()
            if record:
                record.is_archived = True
                record.updated_at = datetime.utcnow()
                db.add(record)
                await db.commit()
