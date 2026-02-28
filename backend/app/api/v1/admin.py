from fastapi import APIRouter, Depends, Query, HTTPException, Request
from typing import Any, Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from pydantic import BaseModel
import platform

from datetime import datetime, timedelta
from uuid import UUID

from app.core.db import get_db
from app.core import security
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.models import (
    EmailLog, EmailOutbox, EmailOutboxStatus,
    SystemModuleConfig, User, AdminAuditLog,
    Workspace, WorkspaceMember,
    WebhookEventLog,
    Message, DeliveryStatus,
    Flow, FlowStatus,
    PromptConfig,
    Integration, ZohoLeadMapping,
    ExecutionInstance,
    Plan, PlanEntitlement, WorkspacePlan,
    WorkspaceEntitlementOverride, UsageMeter,
    AgencyAccount, AgencyMember, AgencyStatus, WorkspaceOwnership,
    RuntimeEventLog,
    QualificationConfig,
    AutomationTemplate, AutomationTemplateVersion,
)
from app.domain.builder_translator import validate_graph, translate
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.modules import module_cache, ALL_MODULES, MODULE_ADMIN_PORTAL
from app.core.audit import log_admin_action
from app.services.audit_service import audit_event
from app.services.settings_service import (
    get_system_settings as _get_system_settings,
    patch_system_settings as _patch_system_settings,
)

router = APIRouter()


# ─── Internal superadmin guard ────────────────────────────────────────────────
# Uses the real OAuth2/Bearer dependency chain (same as all other routes).

async def require_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Raise 403 if the authenticated user is not a SuperAdmin."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin privileges required")
    return current_user


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ModuleToggleRequest(BaseModel):
    enabled: bool
    config_json: Optional[Dict[str, Any]] = None

class ModuleRead(BaseModel):
    module_name: str
    is_enabled: bool
    config_json: Optional[Dict] = None
    updated_at: Optional[Any] = None

    class Config:
        from_attributes = True


# ─── Email Log Endpoints ──────────────────────────────────────────────────────

@router.get("/email-logs", response_model=ResponseEnvelope[dict])
async def get_email_logs(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    email_type: Optional[str] = None
) -> Any:
    """Get paginated email logs - superadmin only"""
    query = select(EmailLog)

    if status:
        query = query.where(EmailLog.status == status)
    if email_type:
        query = query.where(EmailLog.email_type == email_type)

    query = query.order_by(EmailLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return wrap_data({
        "items": [log.model_dump() for log in logs],
        "skip": skip,
        "limit": limit
    })

@router.get("/email-logs/{log_id}", response_model=ResponseEnvelope[dict])
async def get_email_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin)
) -> Any:
    """Get single email log by id."""
    log = await db.get(EmailLog, log_id)
    if not log:
        return wrap_error("Email log not found")
    return wrap_data(log.model_dump())


# ─── Module Endpoints ─────────────────────────────────────────────────────────

@router.get("/modules", response_model=ResponseEnvelope[List[ModuleRead]])
async def list_modules(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """List all system modules and their current enabled/disabled state."""
    result = await db.execute(select(SystemModuleConfig))
    db_modules = {m.module_name: m for m in result.scalars().all()}

    output = []
    for module_name in ALL_MODULES:
        if module_name in db_modules:
            m = db_modules[module_name]
            output.append(ModuleRead(
                module_name=m.module_name,
                is_enabled=m.is_enabled,
                config_json=m.config_json,
                updated_at=m.updated_at
            ))
        else:
            # Not yet seeded: default to enabled
            output.append(ModuleRead(module_name=module_name, is_enabled=True))

    return wrap_data(output)


@router.patch("/modules/{module_name}", response_model=ResponseEnvelope[ModuleRead])
async def toggle_module(
    module_name: str,
    payload: ModuleToggleRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin)
) -> Any:
    """Toggle a system module on or off. The admin_portal module cannot be disabled."""
    # Guard: admin_portal must always stay enabled
    if module_name == MODULE_ADMIN_PORTAL and not payload.enabled:
        raise HTTPException(
            status_code=400,
            detail="MODULE_LOCKED: The 'admin_portal' module cannot be disabled."
        )

    result = await db.execute(
        select(SystemModuleConfig).where(SystemModuleConfig.module_name == module_name)
    )
    mod = result.scalars().first()

    previous_state = mod.is_enabled if mod else True

    if not mod:
        mod = SystemModuleConfig(
            module_name=module_name,
            is_enabled=payload.enabled,
            config_json=payload.config_json,
            updated_by_user_id=admin_user.id
        )
        db.add(mod)
    else:
        mod.is_enabled = payload.enabled
        mod.updated_by_user_id = admin_user.id
        if payload.config_json is not None:
            mod.config_json = payload.config_json

    # Audit log
    await log_admin_action(
        db=db,
        actor_user_id=admin_user.id,
        action="module_toggle",
        entity_type="system_module",
        entity_id=module_name,
        metadata={
            "previous_state": previous_state,
            "new_state": payload.enabled,
            "config_json_changed": payload.config_json is not None,
        }
    )

    await db.commit()
    await db.refresh(mod)

    # Invalidate cache so change takes effect within one tick
    module_cache.invalidate(module_name)

    return wrap_data(ModuleRead(
        module_name=mod.module_name,
        is_enabled=mod.is_enabled,
        config_json=mod.config_json,
        updated_at=mod.updated_at
    ))


# ─── System Overview Endpoint ─────────────────────────────────────────────────

@router.get("/overview", response_model=ResponseEnvelope[dict])
async def get_system_overview(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Return system-wide health info and counters."""
    from app.models.models import User as UserModel, Workspace, AdminAuditLog as AuditModel

    user_count_res = await db.execute(select(func.count(UserModel.id)))
    user_count = user_count_res.scalar_one() or 0

    workspace_count_res = await db.execute(select(func.count(Workspace.id)))
    workspace_count = workspace_count_res.scalar_one() or 0

    audit_count_res = await db.execute(select(func.count(AuditModel.id)))
    audit_count = audit_count_res.scalar_one() or 0

    module_res = await db.execute(
        select(SystemModuleConfig.module_name, SystemModuleConfig.is_enabled)
    )
    modules_status = {row[0]: bool(row[1]) for row in module_res.all()}

    return wrap_data({
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "users_total": user_count,
        "workspaces_total": workspace_count,
        "audit_log_entries": audit_count,
        "modules": modules_status,
    })


# ─── Admin Audit Log Endpoint ─────────────────────────────────────────────────

@router.get("/audit-log", response_model=ResponseEnvelope[dict])
async def get_audit_log(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    actor_user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    workspace_id: Optional[str] = None,
    agency_id: Optional[str] = None,
    actor_type: Optional[str] = None,
    outcome: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Any:
    """Return paginated admin audit log entries with filters."""
    from datetime import datetime
    query = select(AdminAuditLog)

    if actor_user_id:
        query = query.where(AdminAuditLog.actor_user_id == actor_user_id)
    if entity_type:
        query = query.where(AdminAuditLog.entity_type == entity_type)
    if action:
        query = query.where(AdminAuditLog.action == action)
    if workspace_id:
        query = query.where(AdminAuditLog.workspace_id == UUID(workspace_id))
    if agency_id:
        query = query.where(AdminAuditLog.agency_id == UUID(agency_id))
    if actor_type:
        query = query.where(AdminAuditLog.actor_type == actor_type)
    if outcome:
        query = query.where(AdminAuditLog.outcome == outcome)
    if correlation_id:
        query = query.where(AdminAuditLog.correlation_id == UUID(correlation_id))
    if date_from:
        try:
            query = query.where(AdminAuditLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.where(AdminAuditLog.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    # Filtered count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(AdminAuditLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    entries = result.scalars().all()

    return wrap_data({
        "items": [
            {
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
            for e in entries
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    })


@router.get("/audit-log/{log_id}", response_model=ResponseEnvelope[dict])
async def get_audit_log_detail(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Get a single audit log entry by ID."""
    entry = await db.get(AdminAuditLog, UUID(log_id))
    if not entry:
        return wrap_error("Audit log entry not found")

    return wrap_data({
        "id": str(entry.id),
        "actor_user_id": str(entry.actor_user_id) if entry.actor_user_id else None,
        "actor_type": entry.actor_type,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "outcome": entry.outcome,
        "workspace_id": str(entry.workspace_id) if entry.workspace_id else None,
        "agency_id": str(entry.agency_id) if entry.agency_id else None,
        "metadata_json": entry.metadata_json,
        "correlation_id": str(entry.correlation_id) if entry.correlation_id else None,
        "ip_address": entry.ip_address,
        "user_agent": entry.user_agent,
        "request_path": entry.request_path,
        "request_method": entry.request_method,
        "error_code": entry.error_code,
        "error_message": entry.error_message,
        "created_at": entry.created_at.isoformat(),
    })


# ─── Runtime Events Endpoints (Mission 18) ────────────────────────────────────

def _rt_event_to_dict(e: RuntimeEventLog) -> dict:
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


@router.get("/runtime-events", response_model=ResponseEnvelope[dict])
async def list_runtime_events(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    workspace_id: Optional[str] = None,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    outcome: Optional[str] = None,
    correlation_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Any:
    """List all runtime events (admin only)."""
    from datetime import datetime
    query = select(RuntimeEventLog)

    if workspace_id:
        query = query.where(RuntimeEventLog.workspace_id == UUID(workspace_id))
    if source:
        query = query.where(RuntimeEventLog.source == source)
    if event_type:
        query = query.where(RuntimeEventLog.event_type == event_type)
    if outcome:
        query = query.where(RuntimeEventLog.outcome == outcome)
    if correlation_id:
        query = query.where(RuntimeEventLog.correlation_id == correlation_id)
    if date_from:
        try:
            query = query.where(RuntimeEventLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.where(RuntimeEventLog.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(RuntimeEventLog.created_at.desc()).offset(skip).limit(limit)
    entries = (await db.execute(query)).scalars().all()

    return wrap_data({
        "items": [_rt_event_to_dict(e) for e in entries],
        "total": total,
        "skip": skip,
        "limit": limit,
    })


@router.get("/runtime-events/{event_id}", response_model=ResponseEnvelope[dict])
async def get_runtime_event_detail(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Get a single runtime event by ID (admin only)."""
    entry = await db.get(RuntimeEventLog, UUID(event_id))
    if not entry:
        return wrap_error("Runtime event not found")

    return wrap_data(_rt_event_to_dict(entry))


# ─── Users Endpoints ─────────────────────────────────────────────────────────

@router.get("/users", response_model=ResponseEnvelope[dict])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    query: Optional[str] = None,
) -> Any:
    """List all users with optional search."""
    stmt = select(User)
    if query:
        stmt = stmt.where(
            User.email.ilike(f"%{query}%") | User.full_name.ilike(f"%{query}%")
        )

    count_stmt = select(func.count(User.id))
    if query:
        count_stmt = count_stmt.where(
            User.email.ilike(f"%{query}%") | User.full_name.ilike(f"%{query}%")
        )
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one() or 0

    stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "auth_provider": u.auth_provider,
                "email_verified_at": u.email_verified_at.isoformat() if u.email_verified_at else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
    })


class UserToggleRequest(BaseModel):
    is_active: bool


@router.post("/users/{user_id}/toggle", response_model=ResponseEnvelope[dict])
async def toggle_user_status(
    user_id: str,
    payload: UserToggleRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Enable or disable a user."""
    user = await db.get(User, UUID(user_id))
    if not user:
        return wrap_error("User not found")

    user.is_active = payload.is_active
    await db.commit()

    await log_admin_action(
        db=db,
        actor_user_id=admin_user.id,
        action="user_toggle",
        entity_type="user",
        entity_id=user_id,
        metadata={"is_active": payload.is_active},
    )

    return wrap_data({"id": str(user.id), "is_active": user.is_active})


@router.post("/users/{user_id}/impersonate", response_model=ResponseEnvelope[dict])
async def impersonate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Generate a short-lived impersonation token for a user."""
    user = await db.get(User, UUID(user_id))
    if not user:
        return wrap_error("User not found")

    # Get user's first workspace
    result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user.id).limit(1)
    )
    membership = result.scalars().first()
    workspace_id = membership.workspace_id if membership else None

    token = security.create_access_token(
        user.id,
        workspace_id=str(workspace_id) if workspace_id else None,
        expires_delta=timedelta(minutes=30),
    )

    await log_admin_action(
        db=db,
        actor_user_id=admin_user.id,
        action="impersonate",
        entity_type="user",
        entity_id=user_id,
    )

    return wrap_data({"access_token": token})


# ─── Workspaces Endpoints ────────────────────────────────────────────────────

@router.get("/workspaces", response_model=ResponseEnvelope[dict])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    query: Optional[str] = None,
) -> Any:
    """List all workspaces."""
    stmt = select(Workspace)
    if query:
        stmt = stmt.where(Workspace.name.ilike(f"%{query}%"))

    count_stmt = select(func.count(Workspace.id))
    if query:
        count_stmt = count_stmt.where(Workspace.name.ilike(f"%{query}%"))
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one() or 0

    stmt = stmt.order_by(Workspace.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    workspaces = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(w.id),
                "name": w.name,
                "subscription_tier": w.subscription_tier,
                "created_at": w.created_at.isoformat(),
            }
            for w in workspaces
        ],
        "total": total,
    })


@router.get("/workspaces/{workspace_id}", response_model=ResponseEnvelope[dict])
async def get_workspace_detail(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Get workspace detail including member count."""
    ws = await db.get(Workspace, UUID(workspace_id))
    if not ws:
        return wrap_error("Workspace not found")

    member_count_res = await db.execute(
        select(func.count(WorkspaceMember.user_id)).where(
            WorkspaceMember.workspace_id == ws.id
        )
    )
    member_count = member_count_res.scalar_one() or 0

    return wrap_data({
        "id": str(ws.id),
        "name": ws.name,
        "subscription_tier": ws.subscription_tier,
        "created_at": ws.created_at.isoformat(),
        "member_count": member_count,
    })


@router.get("/workspaces/{workspace_id}/modules", response_model=ResponseEnvelope[list])
async def get_workspace_modules(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Get per-workspace module override status."""
    # Get global module states
    global_res = await db.execute(select(SystemModuleConfig))
    global_modules = {m.module_name: m.is_enabled for m in global_res.scalars().all()}

    output = []
    for module_name in ALL_MODULES:
        global_enabled = global_modules.get(module_name, True)
        output.append({
            "module_name": module_name,
            "is_enabled": global_enabled,
            "overridden": False,
        })

    return wrap_data(output)


class WorkspaceModuleToggle(BaseModel):
    is_enabled: bool


@router.patch("/workspaces/{workspace_id}/modules/{module_name}", response_model=ResponseEnvelope[dict])
async def set_workspace_module(
    workspace_id: str,
    module_name: str,
    payload: WorkspaceModuleToggle,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Set a per-workspace module override (uses global toggle for now)."""
    result = await db.execute(
        select(SystemModuleConfig).where(SystemModuleConfig.module_name == module_name)
    )
    mod = result.scalars().first()
    if not mod:
        return wrap_error(f"Module '{module_name}' not found")

    mod.is_enabled = payload.is_enabled
    mod.updated_by_user_id = admin_user.id
    await db.commit()
    module_cache.invalidate(module_name)

    await audit_event(
        db, action="workspace_module_set", entity_type="module",
        entity_id=module_name, actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
        metadata={"workspace_id": workspace_id, "is_enabled": payload.is_enabled},
    )
    await db.commit()
    return wrap_data({
        "module_name": module_name,
        "is_enabled": payload.is_enabled,
        "workspace_id": workspace_id,
    })


# ─── Email Retry Endpoint ────────────────────────────────────────────────────

@router.post("/email-logs/{outbox_id}/retry", response_model=ResponseEnvelope[dict])
async def retry_email(
    outbox_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Re-queue a failed email for retry."""
    outbox = await db.get(EmailOutbox, UUID(outbox_id))
    if not outbox:
        return wrap_error("Email outbox entry not found")

    outbox.status = EmailOutboxStatus.PENDING
    outbox.attempt_count = 0
    outbox.last_error = None
    await db.commit()

    try:
        from app.workers.email_tasks import send_email_task_v2
        send_email_task_v2.delay(str(outbox.id))
    except Exception:
        pass

    await audit_event(
        db, action="email_retry", entity_type="email_outbox",
        entity_id=outbox_id, actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
    )
    await db.commit()
    return wrap_data({"message": "Email re-queued for retry", "outbox_id": str(outbox.id)})


# ─── Webhooks Endpoints ──────────────────────────────────────────────────────

@router.get("/webhooks", response_model=ResponseEnvelope[dict])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    provider: Optional[str] = None,
    status: Optional[str] = None,
) -> Any:
    """List webhook event logs."""
    stmt = select(WebhookEventLog)
    if provider:
        stmt = stmt.where(WebhookEventLog.provider == provider)
    if status:
        stmt = stmt.where(WebhookEventLog.status == status)

    stmt = stmt.order_by(WebhookEventLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(e.id),
                "provider": e.provider,
                "provider_event_id": e.provider_event_id,
                "status": e.status,
                "attempts": e.attempts,
                "last_error": e.last_error,
                "created_at": e.created_at.isoformat(),
                "processed_at": e.processed_at.isoformat() if e.processed_at else None,
            }
            for e in events
        ],
    })


@router.post("/webhooks/{event_id}/replay", response_model=ResponseEnvelope[dict])
async def replay_webhook(
    event_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Reset a webhook event to RECEIVED so it gets reprocessed."""
    event = await db.get(WebhookEventLog, UUID(event_id))
    if not event:
        return wrap_error("Webhook event not found")

    event.status = "received"
    event.attempts = 0
    event.last_error = None
    event.processed_at = None
    await db.commit()

    await audit_event(
        db, action="webhook_replay", entity_type="webhook_event",
        entity_id=event_id, actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
    )
    await db.commit()
    return wrap_data({"message": "Webhook event reset for replay", "id": str(event.id)})


# ─── Dispatch Endpoints ──────────────────────────────────────────────────────

@router.get("/dispatch", response_model=ResponseEnvelope[dict])
async def list_dispatch_queue(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List messages in the dispatch queue."""
    count_res = await db.execute(select(func.count(Message.id)))
    total = count_res.scalar_one() or 0

    stmt = (
        select(Message)
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(m.id),
                "conversation_id": str(m.conversation_id),
                "direction": m.direction,
                "platform": m.platform,
                "delivery_status": m.delivery_status,
                "attempt_count": m.attempt_count,
                "last_error": m.last_error,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total": total,
    })


@router.patch("/dispatch/{message_id}/retry", response_model=ResponseEnvelope[dict])
async def retry_dispatch(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Reset a failed message for retry."""
    msg = await db.get(Message, UUID(message_id))
    if not msg:
        return wrap_error("Message not found")

    msg.delivery_status = DeliveryStatus.PENDING
    msg.attempt_count = 0
    msg.last_error = None
    await db.commit()

    await audit_event(
        db, action="dispatch_retry", entity_type="message",
        entity_id=message_id, actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
    )
    await db.commit()
    return wrap_data({"message": "Message reset for retry", "id": str(msg.id)})


@router.patch("/dispatch/{message_id}/dead-letter", response_model=ResponseEnvelope[dict])
async def dead_letter_dispatch(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Move a message to dead-letter (mark as failed permanently)."""
    msg = await db.get(Message, UUID(message_id))
    if not msg:
        return wrap_error("Message not found")

    msg.delivery_status = DeliveryStatus.FAILED
    msg.last_error = "Moved to dead-letter by admin"
    await db.commit()

    await audit_event(
        db, action="dispatch_dead_letter", entity_type="message",
        entity_id=message_id, actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
    )
    await db.commit()
    return wrap_data({"message": "Message moved to dead-letter", "id": str(msg.id)})


# ─── Automations Endpoints ───────────────────────────────────────────────────

@router.get("/automations", response_model=ResponseEnvelope[dict])
async def list_automations(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List all automation flows across all workspaces."""
    count_res = await db.execute(select(func.count(Flow.id)))
    total = count_res.scalar_one() or 0

    stmt = select(Flow).order_by(Flow.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    flows = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(f.id),
                "name": f.name,
                "workspace_id": str(f.workspace_id),
                "status": f.status,
                "description": f.description,
                "created_at": f.created_at.isoformat(),
            }
            for f in flows
        ],
        "total": total,
    })


@router.patch("/automations/{flow_id}/disable", response_model=ResponseEnvelope[dict])
async def disable_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Disable (set to draft) an automation flow."""
    flow = await db.get(Flow, UUID(flow_id))
    if not flow:
        return wrap_error("Flow not found")

    flow.status = FlowStatus.DRAFT
    await db.commit()

    await log_admin_action(
        db=db,
        actor_user_id=admin_user.id,
        action="flow_disable",
        entity_type="flow",
        entity_id=flow_id,
        metadata={"workspace_id": str(flow.workspace_id)},
    )

    return wrap_data({"message": "Flow disabled", "id": str(flow.id)})


# ─── Prompt Configs Endpoint ─────────────────────────────────────────────────

@router.get("/prompt-configs", response_model=ResponseEnvelope[dict])
async def list_prompt_configs(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List all prompt configs across all workspaces."""
    count_res = await db.execute(select(func.count(PromptConfig.id)))
    total = count_res.scalar_one() or 0

    stmt = select(PromptConfig).order_by(PromptConfig.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    configs = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(c.id),
                "name": c.name,
                "workspace_id": str(c.workspace_id),
                "current_version_id": str(c.current_version_id) if c.current_version_id else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in configs
        ],
        "total": total,
    })


# ─── Zoho Health Endpoint ────────────────────────────────────────────────────

@router.get("/zoho-health", response_model=ResponseEnvelope[dict])
async def get_zoho_health(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Return Zoho integration health across all workspaces."""
    result = await db.execute(
        select(Integration).where(Integration.provider == "zoho")
    )
    integrations = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(i.id),
                "workspace_id": str(i.workspace_id),
                "status": i.status,
                "provider_workspace_id": i.provider_workspace_id,
                "connected_at": i.connected_at.isoformat() if i.connected_at else None,
                "last_checked_at": i.last_checked_at.isoformat() if i.last_checked_at else None,
                "last_error": i.last_error,
            }
            for i in integrations
        ],
    })


# ─── Monitoring Endpoints ────────────────────────────────────────────────────

@router.get("/integrations", response_model=ResponseEnvelope[dict])
async def list_all_integrations(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """List all integrations across all workspaces (monitoring)."""
    result = await db.execute(
        select(Integration).order_by(Integration.created_at.desc())
    )
    integrations = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(i.id),
                "workspace_id": str(i.workspace_id),
                "provider": i.provider,
                "status": i.status,
                "provider_workspace_id": i.provider_workspace_id,
                "connected_at": i.connected_at.isoformat() if i.connected_at else None,
                "last_error": i.last_error,
            }
            for i in integrations
        ],
    })


@router.get("/executions", response_model=ResponseEnvelope[dict])
async def list_executions(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """List recent execution instances across all workspaces (monitoring)."""
    stmt = (
        select(ExecutionInstance)
        .order_by(ExecutionInstance.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    executions = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(e.id),
                "workspace_id": str(e.workspace_id),
                "flow_version_id": str(e.flow_version_id),
                "status": e.status,
                "created_at": e.created_at.isoformat(),
            }
            for e in executions
        ],
    })


# ─── Plans & Entitlements (Mission 14) ──────────────────────────────────────

class PlanCreateRequest(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int = 0

class PlanUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

class EntitlementItem(BaseModel):
    module_key: str
    hard_limit: Optional[int] = None

class EntitlementsBulkRequest(BaseModel):
    entitlements: List[EntitlementItem]

class AssignPlanRequest(BaseModel):
    plan_id: str

class OverrideItem(BaseModel):
    module_key: str
    hard_limit: Optional[int] = None

class OverridesBulkRequest(BaseModel):
    overrides: List[OverrideItem]


def _plan_to_dict(plan: Plan, entitlements: list = None, workspace_count: int = 0) -> dict:
    d = {
        "id": str(plan.id),
        "name": plan.name,
        "display_name": plan.display_name,
        "description": plan.description,
        "is_active": plan.is_active,
        "sort_order": plan.sort_order,
        "created_at": plan.created_at.isoformat(),
        "workspace_count": workspace_count,
    }
    if entitlements is not None:
        d["entitlements"] = [
            {"module_key": e.module_key, "hard_limit": e.hard_limit}
            for e in entitlements
        ]
    return d


@router.get("/plans", response_model=ResponseEnvelope[dict])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """List all plans with entitlement counts and workspace counts."""
    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    plans = result.scalars().all()

    items = []
    for plan in plans:
        # Count entitlements
        ent_res = await db.execute(
            select(func.count(PlanEntitlement.id)).where(PlanEntitlement.plan_id == plan.id)
        )
        ent_count = ent_res.scalar_one() or 0

        # Count workspaces on this plan
        ws_res = await db.execute(
            select(func.count(WorkspacePlan.id)).where(WorkspacePlan.plan_id == plan.id)
        )
        ws_count = ws_res.scalar_one() or 0

        items.append({
            "id": str(plan.id),
            "name": plan.name,
            "display_name": plan.display_name,
            "description": plan.description,
            "is_active": plan.is_active,
            "sort_order": plan.sort_order,
            "entitlement_count": ent_count,
            "workspace_count": ws_count,
            "created_at": plan.created_at.isoformat(),
        })

    return wrap_data({"items": items})


@router.post("/plans", response_model=ResponseEnvelope[dict])
async def create_plan(
    payload: PlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Create a new plan."""
    plan = Plan(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    await log_admin_action(
        db=db, actor_user_id=admin_user.id,
        action="plan_create", entity_type="plan", entity_id=str(plan.id),
    )

    return wrap_data(_plan_to_dict(plan, entitlements=[], workspace_count=0))


@router.get("/plans/{plan_id}", response_model=ResponseEnvelope[dict])
async def get_plan_detail(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Get plan detail with entitlements."""
    plan = await db.get(Plan, UUID(plan_id))
    if not plan:
        return wrap_error("Plan not found")

    ent_res = await db.execute(
        select(PlanEntitlement).where(PlanEntitlement.plan_id == plan.id)
    )
    entitlements = ent_res.scalars().all()

    ws_res = await db.execute(
        select(func.count(WorkspacePlan.id)).where(WorkspacePlan.plan_id == plan.id)
    )
    ws_count = ws_res.scalar_one() or 0

    return wrap_data(_plan_to_dict(plan, entitlements=entitlements, workspace_count=ws_count))


@router.put("/plans/{plan_id}", response_model=ResponseEnvelope[dict])
async def update_plan(
    plan_id: str,
    payload: PlanUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Update plan metadata."""
    plan = await db.get(Plan, UUID(plan_id))
    if not plan:
        return wrap_error("Plan not found")

    if payload.display_name is not None:
        plan.display_name = payload.display_name
    if payload.description is not None:
        plan.description = payload.description
    if payload.is_active is not None:
        plan.is_active = payload.is_active
    if payload.sort_order is not None:
        plan.sort_order = payload.sort_order

    await db.commit()
    await db.refresh(plan)

    await log_admin_action(
        db=db, actor_user_id=admin_user.id,
        action="plan_update", entity_type="plan", entity_id=str(plan.id),
    )

    return wrap_data(_plan_to_dict(plan))


@router.put("/plans/{plan_id}/entitlements", response_model=ResponseEnvelope[dict])
async def set_plan_entitlements(
    plan_id: str,
    payload: EntitlementsBulkRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Bulk-set entitlements for a plan (replaces all existing)."""
    plan = await db.get(Plan, UUID(plan_id))
    if not plan:
        return wrap_error("Plan not found")

    # Delete existing entitlements
    existing = await db.execute(
        select(PlanEntitlement).where(PlanEntitlement.plan_id == plan.id)
    )
    for ent in existing.scalars().all():
        await db.delete(ent)

    # Insert new ones
    new_ents = []
    for item in payload.entitlements:
        ent = PlanEntitlement(
            plan_id=plan.id,
            module_key=item.module_key,
            hard_limit=item.hard_limit,
        )
        db.add(ent)
        new_ents.append(ent)

    await db.commit()

    await log_admin_action(
        db=db, actor_user_id=admin_user.id,
        action="plan_entitlements_set", entity_type="plan", entity_id=str(plan.id),
        metadata={"count": len(new_ents)},
    )

    return wrap_data(_plan_to_dict(plan, entitlements=new_ents))


# ─── Workspace Plan Assignment ──────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/plan", response_model=ResponseEnvelope[dict])
async def get_workspace_plan(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Get workspace's current plan and usage summary."""
    ws = await db.get(Workspace, UUID(workspace_id))
    if not ws:
        return wrap_error("Workspace not found")

    wp_res = await db.execute(
        select(WorkspacePlan).where(WorkspacePlan.workspace_id == ws.id)
    )
    wp = wp_res.scalars().first()

    if not wp:
        return wrap_data({"plan": None, "message": "No plan assigned"})

    plan = await db.get(Plan, wp.plan_id)

    # Get entitlements
    ent_res = await db.execute(
        select(PlanEntitlement).where(PlanEntitlement.plan_id == wp.plan_id)
    )
    entitlements = ent_res.scalars().all()

    # Get overrides
    override_res = await db.execute(
        select(WorkspaceEntitlementOverride).where(
            WorkspaceEntitlementOverride.workspace_id == ws.id
        )
    )
    overrides = {o.module_key: o.hard_limit for o in override_res.scalars().all()}

    # Get current month usage
    from app.services.entitlements import _current_period
    period = _current_period()
    usage_res = await db.execute(
        select(UsageMeter).where(
            UsageMeter.workspace_id == ws.id,
            UsageMeter.period == period,
        )
    )
    usage_map = {u.module_key: u.counter for u in usage_res.scalars().all()}

    return wrap_data({
        "plan": {
            "id": str(plan.id),
            "name": plan.name,
            "display_name": plan.display_name,
        } if plan else None,
        "assigned_at": wp.assigned_at.isoformat(),
        "entitlements": [
            {
                "module_key": e.module_key,
                "plan_limit": e.hard_limit,
                "effective_limit": overrides.get(e.module_key, e.hard_limit),
                "has_override": e.module_key in overrides,
                "used": usage_map.get(e.module_key, 0),
            }
            for e in entitlements
        ],
    })


@router.put("/workspaces/{workspace_id}/plan", response_model=ResponseEnvelope[dict])
async def assign_workspace_plan(
    workspace_id: str,
    payload: AssignPlanRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Assign or change a workspace's plan."""
    ws = await db.get(Workspace, UUID(workspace_id))
    if not ws:
        return wrap_error("Workspace not found")

    plan = await db.get(Plan, UUID(payload.plan_id))
    if not plan:
        return wrap_error("Plan not found")

    wp_res = await db.execute(
        select(WorkspacePlan).where(WorkspacePlan.workspace_id == ws.id)
    )
    wp = wp_res.scalars().first()

    from datetime import datetime
    if wp:
        old_plan_id = str(wp.plan_id)
        wp.plan_id = plan.id
        wp.assigned_by = admin_user.id
        wp.assigned_at = datetime.utcnow()
    else:
        old_plan_id = None
        wp = WorkspacePlan(
            workspace_id=ws.id,
            plan_id=plan.id,
            assigned_by=admin_user.id,
        )
        db.add(wp)

    # Also update the legacy subscription_tier field
    ws.subscription_tier = plan.name
    await db.commit()

    await log_admin_action(
        db=db, actor_user_id=admin_user.id,
        action="workspace_plan_assign", entity_type="workspace", entity_id=workspace_id,
        metadata={"old_plan_id": old_plan_id, "new_plan_id": str(plan.id)},
    )

    return wrap_data({
        "workspace_id": workspace_id,
        "plan_id": str(plan.id),
        "plan_name": plan.display_name,
    })


@router.get("/workspaces/{workspace_id}/usage", response_model=ResponseEnvelope[dict])
async def get_workspace_usage(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Get workspace usage meters for the current month."""
    from app.services.entitlements import _current_period
    period = _current_period()

    result = await db.execute(
        select(UsageMeter).where(
            UsageMeter.workspace_id == UUID(workspace_id),
            UsageMeter.period == period,
        )
    )
    meters = result.scalars().all()

    return wrap_data({
        "workspace_id": workspace_id,
        "period": period,
        "meters": [
            {
                "module_key": m.module_key,
                "counter": m.counter,
            }
            for m in meters
        ],
    })


@router.put("/workspaces/{workspace_id}/overrides", response_model=ResponseEnvelope[dict])
async def set_workspace_overrides(
    workspace_id: str,
    payload: OverridesBulkRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Set entitlement overrides for a workspace (upsert)."""
    ws_id = UUID(workspace_id)

    for item in payload.overrides:
        result = await db.execute(
            select(WorkspaceEntitlementOverride).where(
                WorkspaceEntitlementOverride.workspace_id == ws_id,
                WorkspaceEntitlementOverride.module_key == item.module_key,
            )
        )
        existing = result.scalars().first()
        if existing:
            existing.hard_limit = item.hard_limit
        else:
            override = WorkspaceEntitlementOverride(
                workspace_id=ws_id,
                module_key=item.module_key,
                hard_limit=item.hard_limit,
            )
            db.add(override)

    await db.commit()

    await log_admin_action(
        db=db, actor_user_id=admin_user.id,
        action="workspace_overrides_set", entity_type="workspace", entity_id=workspace_id,
        metadata={"count": len(payload.overrides)},
    )

    return wrap_data({"message": f"Set {len(payload.overrides)} override(s)", "workspace_id": workspace_id})


@router.delete("/workspaces/{workspace_id}/overrides/{module_key}", response_model=ResponseEnvelope[dict])
async def remove_workspace_override(
    workspace_id: str,
    module_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Remove a specific entitlement override for a workspace."""
    result = await db.execute(
        select(WorkspaceEntitlementOverride).where(
            WorkspaceEntitlementOverride.workspace_id == UUID(workspace_id),
            WorkspaceEntitlementOverride.module_key == module_key,
        )
    )
    override = result.scalars().first()
    if not override:
        return wrap_error(f"No override found for module '{module_key}'")

    await db.delete(override)
    await audit_event(
        db, action="workspace_override_remove", entity_type="entitlement_override",
        entity_id=f"{workspace_id}:{module_key}", actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
        metadata={"workspace_id": workspace_id, "module_key": module_key},
    )
    await db.commit()

    return wrap_data({"message": f"Override for '{module_key}' removed", "workspace_id": workspace_id})


# ─── Agency Admin Endpoints (Mission 15) ─────────────────────────────────────

class AgencyStatusUpdateRequest(BaseModel):
    status: AgencyStatus

class AgencyPlanAssignRequest(BaseModel):
    plan_id: str


@router.get("/agencies", response_model=ResponseEnvelope[dict])
async def list_agencies(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    query: Optional[str] = None,
) -> Any:
    """List all agencies (paginated, searchable by name or owner email)."""
    stmt = select(AgencyAccount, User).join(User, User.id == AgencyAccount.owner_user_id)
    count_stmt = select(func.count(AgencyAccount.id))

    if query:
        filter_clause = AgencyAccount.name.ilike(f"%{query}%") | User.email.ilike(f"%{query}%")
        stmt = stmt.where(filter_clause)
        count_stmt = count_stmt.join(User, User.id == AgencyAccount.owner_user_id).where(filter_clause)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one() or 0

    stmt = stmt.order_by(AgencyAccount.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for agency, owner in rows:
        # Count workspaces
        ws_res = await db.execute(
            select(func.count(WorkspaceOwnership.id)).where(
                WorkspaceOwnership.owner_agency_id == agency.id
            )
        )
        ws_count = ws_res.scalar_one() or 0

        # Count members
        mem_res = await db.execute(
            select(func.count(AgencyMember.id)).where(
                AgencyMember.agency_id == agency.id
            )
        )
        mem_count = mem_res.scalar_one() or 0

        items.append({
            "id": str(agency.id),
            "name": agency.name,
            "status": agency.status.value,
            "owner_email": owner.email,
            "owner_name": owner.full_name,
            "plan_id": str(agency.plan_id) if agency.plan_id else None,
            "workspace_count": ws_count,
            "member_count": mem_count,
            "created_at": agency.created_at.isoformat(),
        })

    return wrap_data({"items": items, "total": total})


@router.get("/agencies/{agency_id}", response_model=ResponseEnvelope[dict])
async def get_agency_detail(
    agency_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Agency detail: members, workspaces, plan."""
    agency = await db.get(AgencyAccount, UUID(agency_id))
    if not agency:
        return wrap_error("Agency not found")

    owner = await db.get(User, agency.owner_user_id)

    # Members
    mem_res = await db.execute(
        select(AgencyMember, User)
        .join(User, User.id == AgencyMember.user_id)
        .where(AgencyMember.agency_id == agency.id)
    )
    members = [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "email": u.email,
            "full_name": u.full_name,
            "role": m.role.value,
        }
        for m, u in mem_res.all()
    ]

    # Workspaces
    ws_res = await db.execute(
        select(Workspace)
        .join(WorkspaceOwnership, WorkspaceOwnership.workspace_id == Workspace.id)
        .where(WorkspaceOwnership.owner_agency_id == agency.id)
    )
    workspaces = [
        {
            "id": str(ws.id),
            "name": ws.name,
            "subscription_tier": ws.subscription_tier,
            "created_at": ws.created_at.isoformat(),
        }
        for ws in ws_res.scalars().all()
    ]

    # Plan info
    plan_info = None
    if agency.plan_id:
        plan = await db.get(Plan, agency.plan_id)
        if plan:
            plan_info = {
                "id": str(plan.id),
                "name": plan.name,
                "display_name": plan.display_name,
            }

    return wrap_data({
        "id": str(agency.id),
        "name": agency.name,
        "status": agency.status.value,
        "owner_email": owner.email if owner else None,
        "plan": plan_info,
        "members": members,
        "workspaces": workspaces,
        "created_at": agency.created_at.isoformat(),
    })


@router.patch("/agencies/{agency_id}/status", response_model=ResponseEnvelope[dict])
async def update_agency_status(
    agency_id: str,
    payload: AgencyStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Suspend or activate an agency."""
    agency = await db.get(AgencyAccount, UUID(agency_id))
    if not agency:
        return wrap_error("Agency not found")

    old_status = agency.status.value
    agency.status = payload.status
    await db.commit()

    await log_admin_action(
        db=db,
        actor_user_id=admin_user.id,
        action="agency_status_update",
        entity_type="agency",
        entity_id=agency_id,
        metadata={"old_status": old_status, "new_status": payload.status.value},
    )

    return wrap_data({
        "id": agency_id,
        "old_status": old_status,
        "new_status": payload.status.value,
    })


@router.put("/agencies/{agency_id}/plan", response_model=ResponseEnvelope[dict])
async def assign_agency_plan(
    agency_id: str,
    payload: AgencyPlanAssignRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Assign a plan to an agency."""
    agency = await db.get(AgencyAccount, UUID(agency_id))
    if not agency:
        return wrap_error("Agency not found")

    plan = await db.get(Plan, UUID(payload.plan_id))
    if not plan:
        return wrap_error("Plan not found")

    old_plan_id = str(agency.plan_id) if agency.plan_id else None
    agency.plan_id = plan.id
    await db.commit()

    await log_admin_action(
        db=db,
        actor_user_id=admin_user.id,
        action="agency_plan_assign",
        entity_type="agency",
        entity_id=agency_id,
        metadata={"old_plan_id": old_plan_id, "new_plan_id": str(plan.id)},
    )

    return wrap_data({
        "agency_id": agency_id,
        "plan_id": str(plan.id),
        "plan_name": plan.display_name,
    })


# ─── System Settings (Mission 16) ────────────────────────────────────────────

class PatchSystemSettingsRequest(BaseModel):
    settings: Dict[str, Any]


@router.get("/system-settings")
async def get_system_settings_endpoint(
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await _get_system_settings(db)
    await db.commit()
    return wrap_data({"settings": result.settings, "version": result.version})


@router.patch("/system-settings")
async def update_system_settings_endpoint(
    payload: PatchSystemSettingsRequest,
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await _patch_system_settings(payload.settings, admin.id, db)
    if not result.success:
        return wrap_error(result.error)

    await log_admin_action(
        db=db,
        actor_user_id=admin.id,
        action="update_system_settings",
        entity_type="system_settings",
        entity_id="global",
        metadata={"version": result.version, "patch_keys": list(payload.settings.keys())},
    )
    await db.commit()
    return wrap_data({"settings": result.settings, "version": result.version})


# ── Qualification Defaults (Mission 20) ──────────────────────────────

from app.api.v1.qualification import DEFAULT_QUESTIONS, DEFAULT_STATUSES


@router.get("/qualification-defaults", response_model=ResponseEnvelope[dict])
async def get_qualification_defaults(
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get global default qualification config."""
    return wrap_data({
        "qualification_questions": DEFAULT_QUESTIONS,
        "qualification_statuses": DEFAULT_STATUSES,
    })


@router.put("/qualification-defaults", response_model=ResponseEnvelope[dict])
async def set_qualification_defaults(
    body: Dict[str, Any],
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Set global default qualification config (stored in system settings)."""
    from app.api.v1 import qualification as qual_mod
    if "qualification_questions" in body:
        qual_mod.DEFAULT_QUESTIONS = body["qualification_questions"]
    if "qualification_statuses" in body:
        qual_mod.DEFAULT_STATUSES = body["qualification_statuses"]
    return wrap_data({
        "qualification_questions": qual_mod.DEFAULT_QUESTIONS,
        "qualification_statuses": qual_mod.DEFAULT_STATUSES,
    })


@router.post("/workspaces/{workspace_id}/qualification-reset", response_model=ResponseEnvelope[dict])
async def reset_workspace_qualification(
    workspace_id: UUID,
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Reset a workspace's qualification config to global defaults."""
    result = await db.execute(
        select(QualificationConfig).where(
            QualificationConfig.workspace_id == workspace_id
        )
    )
    config = result.scalars().first()
    if not config:
        config = QualificationConfig(
            workspace_id=workspace_id,
            qualification_questions=DEFAULT_QUESTIONS,
            qualification_statuses=DEFAULT_STATUSES,
        )
        db.add(config)
    else:
        config.qualification_questions = DEFAULT_QUESTIONS
        config.qualification_statuses = DEFAULT_STATUSES
        config.version += 1
    await db.commit()
    await db.refresh(config)
    return wrap_data({
        "id": str(config.id),
        "version": config.version,
        "qualification_questions": config.qualification_questions,
        "qualification_statuses": config.qualification_statuses,
    })


# ─── Template Catalog Admin Endpoints (Mission 27) ────────────────────────────

class CreateTemplatePayload(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    category: str = "general"
    industry_tags: List[str] = []
    platforms: List[str] = []
    required_integrations: List[str] = []
    is_featured: bool = False


class PatchTemplatePayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    industry_tags: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    required_integrations: Optional[List[str]] = None


class CreateTemplateVersionPayload(BaseModel):
    builder_graph_json: Dict[str, Any]
    changelog: Optional[str] = None


@router.get("/templates", response_model=ResponseEnvelope[dict])
async def admin_list_templates(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List all automation templates (admin view, includes inactive)."""
    count_res = await db.execute(select(func.count(AutomationTemplate.id)))
    total = count_res.scalar_one() or 0

    result = await db.execute(
        select(AutomationTemplate)
        .order_by(AutomationTemplate.created_at.desc())
        .offset(skip).limit(limit)
    )
    templates = result.scalars().all()

    return wrap_data({
        "items": [
            {
                "id": str(t.id),
                "slug": t.slug,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "industry_tags": t.industry_tags or [],
                "platforms": t.platforms or [],
                "required_integrations": t.required_integrations or [],
                "is_featured": t.is_featured,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
            }
            for t in templates
        ],
        "total": total,
    })


@router.post("/templates", response_model=ResponseEnvelope[dict])
async def admin_create_template(
    payload: CreateTemplatePayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Create a new automation template."""
    # Check slug uniqueness
    existing = await db.execute(
        select(AutomationTemplate).where(AutomationTemplate.slug == payload.slug)
    )
    if existing.scalars().first():
        return wrap_error(f"Template with slug '{payload.slug}' already exists")

    now = datetime.utcnow()
    template = AutomationTemplate(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        industry_tags=payload.industry_tags,
        platforms=payload.platforms,
        required_integrations=payload.required_integrations,
        is_featured=payload.is_featured,
        is_active=True,
        created_by_admin_id=admin_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(template)
    await audit_event(
        db, action="template_create", entity_type="automation_template",
        entity_id=payload.slug, actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
        metadata={"name": payload.name},
    )
    await db.commit()
    await db.refresh(template)

    return wrap_data({"id": str(template.id), "slug": template.slug, "name": template.name})


@router.patch("/templates/{template_id}", response_model=ResponseEnvelope[dict])
async def admin_patch_template(
    template_id: UUID,
    payload: PatchTemplatePayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Update template metadata."""
    template = await db.get(AutomationTemplate, template_id)
    if not template:
        return wrap_error("Template not found")

    if payload.name is not None:
        template.name = payload.name
    if payload.description is not None:
        template.description = payload.description
    if payload.category is not None:
        template.category = payload.category
    if payload.is_featured is not None:
        template.is_featured = payload.is_featured
    if payload.is_active is not None:
        template.is_active = payload.is_active
    if payload.industry_tags is not None:
        template.industry_tags = payload.industry_tags
    if payload.platforms is not None:
        template.platforms = payload.platforms
    if payload.required_integrations is not None:
        template.required_integrations = payload.required_integrations

    template.updated_at = datetime.utcnow()
    db.add(template)

    await audit_event(
        db, action="template_update", entity_type="automation_template",
        entity_id=str(template_id), actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
    )
    await db.commit()
    return wrap_data({"id": str(template.id), "updated": True})


@router.post("/templates/{template_id}/versions", response_model=ResponseEnvelope[dict])
async def admin_create_template_version(
    template_id: UUID,
    payload: CreateTemplateVersionPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Create a new draft version for a template (validates the graph)."""
    template = await db.get(AutomationTemplate, template_id)
    if not template:
        return wrap_error("Template not found")

    # Validate the graph
    errors = validate_graph(payload.builder_graph_json)
    if errors:
        return wrap_data({"valid": False, "errors": errors})

    # Translate to runtime contract for audit/preview
    try:
        translated = translate(payload.builder_graph_json)
    except Exception as e:
        translated = None

    # Get next version number
    version_result = await db.execute(
        select(func.max(AutomationTemplateVersion.version_number))
        .where(AutomationTemplateVersion.template_id == template_id)
    )
    max_ver = version_result.scalar() or 0
    new_ver_num = max_ver + 1

    now = datetime.utcnow()
    version = AutomationTemplateVersion(
        template_id=template_id,
        version_number=new_ver_num,
        builder_graph_json=payload.builder_graph_json,
        translated_definition_json=translated,
        changelog=payload.changelog,
        created_by_admin_id=admin_user.id,
        is_published=False,
        created_at=now,
        updated_at=now,
    )
    db.add(version)

    await audit_event(
        db, action="template_version_create", entity_type="automation_template_version",
        entity_id=str(template_id), actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
        metadata={"version_number": new_ver_num},
    )
    await db.commit()
    await db.refresh(version)

    return wrap_data({
        "valid": True,
        "id": str(version.id),
        "version_number": version.version_number,
    })


@router.post("/templates/{template_id}/publish", response_model=ResponseEnvelope[dict])
async def admin_publish_template(
    template_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """Publish the latest draft version of a template."""
    template = await db.get(AutomationTemplate, template_id)
    if not template:
        return wrap_error("Template not found")

    # Get latest unpublished version
    result = await db.execute(
        select(AutomationTemplateVersion)
        .where(
            AutomationTemplateVersion.template_id == template_id,
            AutomationTemplateVersion.is_published == False,
        )
        .order_by(AutomationTemplateVersion.version_number.desc())
        .limit(1)
    )
    version = result.scalars().first()
    if not version:
        return wrap_error("No unpublished version found to publish")

    now = datetime.utcnow()
    version.is_published = True
    version.published_at = now
    version.updated_at = now
    db.add(version)

    await audit_event(
        db, action="template_publish", entity_type="automation_template_version",
        entity_id=str(template_id), actor_user_id=admin_user.id,
        actor_type="admin", outcome="success", request=request,
        metadata={"version_number": version.version_number},
    )
    await db.commit()

    return wrap_data({
        "published": True,
        "version_number": version.version_number,
        "published_at": now.isoformat(),
    })


@router.get("/templates/{template_id}/versions", response_model=ResponseEnvelope[list])
async def admin_list_template_versions(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
) -> Any:
    """List all versions for a template."""
    template = await db.get(AutomationTemplate, template_id)
    if not template:
        return wrap_error("Template not found")

    result = await db.execute(
        select(AutomationTemplateVersion)
        .where(AutomationTemplateVersion.template_id == template_id)
        .order_by(AutomationTemplateVersion.version_number.desc())
    )
    versions = result.scalars().all()

    return wrap_data([
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "changelog": v.changelog,
            "is_published": v.is_published,
            "published_at": v.published_at.isoformat() if v.published_at else None,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ])
