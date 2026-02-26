from typing import List, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete

from app.api import deps
from app.core.db import get_db
from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole, Invite
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceRead, MemberRead, MemberInvite, MemberUpdateRole
)
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.services.entitlements import get_workspace_entitlements
from app.services.audit_service import audit_event

router = APIRouter()

@router.post("", response_model=ResponseEnvelope[WorkspaceRead])
async def create_workspace(
    *,
    db: AsyncSession = Depends(get_db),
    workspace_in: WorkspaceCreate,
    current_user: User = Depends(deps.get_current_user),
    request: Request,
) -> Any:
    """Create a new workspace and add current user as Owner."""
    workspace = Workspace(name=workspace_in.name)
    db.add(workspace)
    await db.flush()
    
    membership = WorkspaceMember(
        user_id=current_user.id,
        workspace_id=workspace.id,
        role=WorkspaceRole.OWNER
    )
    db.add(membership)
    await audit_event(
        db, action="workspace_create", entity_type="workspace",
        entity_id=str(workspace.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
    )
    await db.commit()
    await db.refresh(workspace)
    return wrap_data(workspace)

@router.get("", response_model=ResponseEnvelope[List[WorkspaceRead]])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """List all workspaces the current user belongs to."""
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == current_user.id)
    )
    workspaces = result.scalars().all()
    return wrap_data(workspaces)

# --- Member Management (Scoped via X-Workspace-ID) ---

@router.get("/members", response_model=ResponseEnvelope[List[MemberRead]])
async def list_members(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """List all members in the active workspace."""
    # In a real app, join with User to get details
    query = (
        select(User.id.label("user_id"), User.email, User.full_name, WorkspaceMember.role)
        .join(WorkspaceMember, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace.id)
    )
    result = await db.execute(query)
    members = [
        {"user_id": row.user_id, "email": row.email, "full_name": row.full_name, "role": row.role}
        for row in result
    ]
    return wrap_data(members)

@router.post("/members/invite", response_model=ResponseEnvelope[dict])
async def invite_member(
    *,
    db: AsyncSession = Depends(get_db),
    invite_in: MemberInvite,
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
    _ = Depends(deps.require_role([WorkspaceRole.OWNER, WorkspaceRole.MEMBER])),
    request: Request,
) -> Any:
    """Invite a new member to the workspace."""
    import secrets
    from datetime import datetime, timedelta
    from app.services.email_service import EmailService

    token = secrets.token_urlsafe(32)
    
    invite = Invite(
        workspace_id=workspace.id,
        email=invite_in.email,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(invite)
    await db.commit()
    
    # Send Email
    # We should get user name if possible, for now using "A member" if not available easily without query
    # But we access current_user via dependency in many places. Here we don't have it explicitly in args 
    # but we can assume the caller is a member. 
    inviter_name = current_user.full_name or current_user.email
    
    await EmailService.send_invite_email(invite.email, invite.token, workspace.name, inviter_name)

    await audit_event(
        db, action="workspace_invite", entity_type="invite",
        entity_id=invite_in.email, actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"invited_email": invite_in.email},
    )
    await db.commit()
    return wrap_data({"message": f"Invite sent to {invite_in.email}"})

@router.delete("/members/{member_id}", response_model=ResponseEnvelope[dict])
async def remove_member(
    member_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
    _ = Depends(deps.require_role([WorkspaceRole.OWNER])),
) -> Any:
    """Remove a member from the workspace."""
    if member_id == workspace.id: # Should be member_id == user.id of owner?
        # Prevent removing oneself if last owner? (Business logic)
        pass
        
    await db.execute(
        delete(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == member_id
        )
    )
    await audit_event(
        db, action="workspace_member_remove", entity_type="workspace_member",
        entity_id=str(member_id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
    )
    await db.commit()
    return wrap_data({"message": "Member removed"})

@router.patch("/members/{member_id}/role", response_model=ResponseEnvelope[dict])
async def update_member_role(
    member_id: UUID,
    role_in: MemberUpdateRole,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
    _ = Depends(deps.require_role([WorkspaceRole.OWNER])),
) -> Any:
    """Update a member's role."""
    result = await db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == member_id
        )
    )
    membership = result.scalars().first()
    if not membership:
        return wrap_error("Member not found")
        
    membership.role = role_in.role
    db.add(membership)
    await audit_event(
        db, action="workspace_role_change", entity_type="workspace_member",
        entity_id=str(member_id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"new_role": role_in.role},
    )
    await db.commit()
    return wrap_data({"message": "Role updated"})


# --- Entitlements (Mission 14) ---

@router.get("/entitlements", response_model=ResponseEnvelope)
async def get_entitlements(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Return merged entitlements + usage for the current workspace."""
    entitlements = await get_workspace_entitlements(workspace.id, db)
    return wrap_data(entitlements)
