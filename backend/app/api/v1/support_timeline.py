"""
Support Timeline Router — Mission 18
Workspace-scoped runtime event timeline endpoints.
"""
from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func as sa_func
from sqlmodel import select, func

from app.core.db import get_db
from app.api.deps import get_active_workspace, require_role
from app.models.models import Workspace, RuntimeEventLog
from app.schemas.envelope import wrap_data, wrap_error

router = APIRouter()


def _event_to_dict(e: RuntimeEventLog) -> dict:
    """Serialize a runtime event entry to a dict."""
    return {
        "id": str(e.id),
        "workspace_id": str(e.workspace_id) if e.workspace_id else None,
        "event_type": e.event_type,
        "source": e.source,
        "correlation_id": e.correlation_id,
        "related_ids": e.related_ids,
        "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
        "payload": e.payload,
        "outcome": e.outcome,
        "error_message": e.error_message,
        "duration_ms": e.duration_ms,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/support/timeline")
async def list_timeline_events(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_active_workspace),
    _=Depends(require_role(["owner", "member", "viewer"])),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    contact_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    outcome: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Any:
    """List runtime event timeline scoped to the current workspace."""
    query = select(RuntimeEventLog).where(RuntimeEventLog.workspace_id == workspace.id)

    if source:
        query = query.where(RuntimeEventLog.source == source)
    if event_type:
        query = query.where(RuntimeEventLog.event_type == event_type)
    if outcome:
        query = query.where(RuntimeEventLog.outcome == outcome)
    if correlation_id:
        query = query.where(RuntimeEventLog.correlation_id == correlation_id)

    # JSON path filters on related_ids using json_extract (SQLite compatible)
    if contact_id:
        query = query.where(
            sa_func.json_extract(RuntimeEventLog.related_ids, "$.contact_id") == contact_id
        )
    if conversation_id:
        query = query.where(
            sa_func.json_extract(RuntimeEventLog.related_ids, "$.conversation_id") == conversation_id
        )
    if execution_id:
        query = query.where(
            sa_func.json_extract(RuntimeEventLog.related_ids, "$.execution_instance_id") == execution_id
        )

    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(RuntimeEventLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(RuntimeEventLog.created_at <= dt)
        except ValueError:
            pass

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(RuntimeEventLog.created_at.desc()).offset(skip).limit(limit)
    entries = (await db.execute(query)).scalars().all()

    return wrap_data({
        "items": [_event_to_dict(e) for e in entries],
        "total": total,
        "skip": skip,
        "limit": limit,
    })


@router.get("/support/timeline/{event_id}")
async def get_timeline_event_detail(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_active_workspace),
    _=Depends(require_role(["owner", "member", "viewer"])),
) -> Any:
    """Get a single runtime event entry (workspace-scoped)."""
    entry = await db.get(RuntimeEventLog, UUID(event_id))
    if not entry or entry.workspace_id != workspace.id:
        return wrap_error("Runtime event not found")

    return wrap_data(_event_to_dict(entry))
