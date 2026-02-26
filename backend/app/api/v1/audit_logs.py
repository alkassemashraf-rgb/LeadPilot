"""
Audit Logs Router — Mission 17
Workspace-scoped audit log endpoints.
"""
from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.db import get_db
from app.api.deps import get_active_workspace
from app.models.models import Workspace, AdminAuditLog
from app.schemas.envelope import wrap_data, wrap_error

router = APIRouter()


def _entry_to_dict(e: AdminAuditLog) -> dict:
    """Serialize an audit entry to a dict."""
    return {
        "id": str(e.id),
        "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
        "actor_type": e.actor_type,
        "action": e.action,
        "entity_type": e.entity_type,
        "entity_id": e.entity_id,
        "outcome": e.outcome,
        "workspace_id": str(e.workspace_id) if e.workspace_id else None,
        "agency_id": str(e.agency_id) if e.agency_id else None,
        "metadata_json": e.metadata_json,
        "correlation_id": str(e.correlation_id) if e.correlation_id else None,
        "ip_address": e.ip_address,
        "user_agent": e.user_agent,
        "request_path": e.request_path,
        "request_method": e.request_method,
        "error_code": e.error_code,
        "error_message": e.error_message,
        "created_at": e.created_at.isoformat(),
    }


@router.get("")
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_active_workspace),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    outcome: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Any:
    """List audit log entries scoped to the current workspace."""
    query = select(AdminAuditLog).where(AdminAuditLog.workspace_id == workspace.id)

    if action:
        query = query.where(AdminAuditLog.action == action)
    if entity_type:
        query = query.where(AdminAuditLog.entity_type == entity_type)
    if actor_user_id:
        query = query.where(AdminAuditLog.actor_user_id == UUID(actor_user_id))
    if outcome:
        query = query.where(AdminAuditLog.outcome == outcome)
    if correlation_id:
        query = query.where(AdminAuditLog.correlation_id == UUID(correlation_id))
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(AdminAuditLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(AdminAuditLog.created_at <= dt)
        except ValueError:
            pass

    # Count (with same filters)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(AdminAuditLog.created_at.desc()).offset(skip).limit(limit)
    entries = (await db.execute(query)).scalars().all()

    return wrap_data({
        "items": [_entry_to_dict(e) for e in entries],
        "total": total,
        "skip": skip,
        "limit": limit,
    })


@router.get("/{log_id}")
async def get_audit_log_detail(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_active_workspace),
) -> Any:
    """Get a single audit log entry (workspace-scoped)."""
    entry = await db.get(AdminAuditLog, UUID(log_id))
    if not entry or entry.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Audit log entry not found")

    return wrap_data(_entry_to_dict(entry))
