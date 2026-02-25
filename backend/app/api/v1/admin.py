from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Any, Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from pydantic import BaseModel
import platform

from datetime import timedelta
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
)
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.modules import module_cache, ALL_MODULES, MODULE_ADMIN_PORTAL
from app.core.audit import log_admin_action

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
) -> Any:
    """Return paginated admin audit log entries."""
    query = select(AdminAuditLog)

    if actor_user_id:
        query = query.where(AdminAuditLog.actor_user_id == actor_user_id)
    if entity_type:
        query = query.where(AdminAuditLog.entity_type == entity_type)
    if action:
        query = query.where(AdminAuditLog.action == action)

    query = query.order_by(AdminAuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()

    count_result = await db.execute(select(func.count(AdminAuditLog.id)))
    total = count_result.scalar_one() or 0

    return wrap_data({
        "items": [
            {
                "id": str(e.id),
                "actor_user_id": str(e.actor_user_id),
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "workspace_id": str(e.workspace_id) if e.workspace_id else None,
                "metadata_json": e.metadata_json,
                "correlation_id": str(e.correlation_id) if e.correlation_id else None,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    })


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

    return wrap_data({
        "module_name": module_name,
        "is_enabled": payload.is_enabled,
        "workspace_id": workspace_id,
    })


# ─── Email Retry Endpoint ────────────────────────────────────────────────────

@router.post("/email-logs/{outbox_id}/retry", response_model=ResponseEnvelope[dict])
async def retry_email(
    outbox_id: str,
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

    return wrap_data({"message": "Message reset for retry", "id": str(msg.id)})


@router.patch("/dispatch/{message_id}/dead-letter", response_model=ResponseEnvelope[dict])
async def dead_letter_dispatch(
    message_id: str,
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
