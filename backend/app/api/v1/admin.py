from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Any, Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from pydantic import BaseModel
import platform

from app.core.db import get_db
from app.api.deps import get_current_user   # ← uses OAuth2PasswordBearer / Bearer header
from app.models.models import EmailLog, SystemModuleConfig, User, AdminAuditLog
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
        return wrap_error("Email log not found", code="NOT_FOUND")
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
