"""
Settings Router — Mission 16
Workspace-scoped settings: GET + PATCH.
"""
from fastapi import APIRouter, Depends
from typing import Any, Dict
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, get_active_workspace, require_role
from app.models.models import User, Workspace, WorkspaceRole
from app.schemas.envelope import wrap_data, wrap_error
from app.core.audit import log_admin_action
from app.services.settings_service import (
    get_workspace_settings,
    patch_workspace_settings,
)

router = APIRouter()


class PatchSettingsRequest(BaseModel):
    settings: Dict[str, Any]


@router.get("")
async def get_settings(
    workspace: Workspace = Depends(get_active_workspace),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await get_workspace_settings(workspace.id, db)
    await db.commit()
    return wrap_data({"settings": result.settings, "version": result.version})


@router.patch("")
async def update_settings(
    payload: PatchSettingsRequest,
    workspace: Workspace = Depends(get_active_workspace),
    user: User = Depends(get_current_user),
    _role: Any = Depends(require_role([WorkspaceRole.OWNER])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await patch_workspace_settings(
        workspace.id, payload.settings, user.id, db,
    )
    if not result.success:
        return wrap_error(result.error)

    await log_admin_action(
        db, user.id, "update_workspace_settings",
        "workspace_settings", str(workspace.id),
        workspace_id=workspace.id,
        metadata={"version": result.version, "patch_keys": list(payload.settings.keys())},
    )
    await db.commit()
    return wrap_data({"settings": result.settings, "version": result.version})
