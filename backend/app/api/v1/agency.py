"""
Agency Router — Mission 15
Endpoints for creating and managing agency accounts, members, and client workspaces.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from pydantic import BaseModel
from uuid import UUID

from app.core.db import get_db
from app.api.deps import get_current_user, _AGENCY_ROLE_TO_WORKSPACE_ROLE
from app.models.models import (
    User, Workspace, WorkspaceMember, WorkspaceRole,
    AgencyAccount, AgencyMember, AgencyStatus, AgencyRole,
    WorkspaceOwnership, OwnerType,
    Plan, PlanEntitlement, WorkspacePlan,
)
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.audit import log_admin_action
from app.services.audit_service import audit_event
from app.services.settings_service import (
    get_agency_settings as _get_agency_settings,
    patch_agency_settings as _patch_agency_settings,
)

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_user_agency(
    user: User, db: AsyncSession
) -> Optional[tuple]:
    """Return (AgencyAccount, AgencyMember) for the user, or None."""
    result = await db.execute(
        select(AgencyAccount, AgencyMember)
        .join(AgencyMember, AgencyMember.agency_id == AgencyAccount.id)
        .where(AgencyMember.user_id == user.id)
    )
    row = result.first()
    if not row:
        return None
    return row[0], row[1]


def require_agency_role(allowed_roles: List[AgencyRole]):
    """Dependency factory: user must be an agency member with one of the allowed roles."""
    async def _check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> tuple:
        pair = await _get_user_agency(user, db)
        if not pair:
            raise HTTPException(status_code=403, detail="You are not a member of any agency")
        agency, member = pair
        if agency.status != AgencyStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="Agency is suspended")
        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires agency role: {', '.join(r.value for r in allowed_roles)}",
            )
        return agency, member, user
    return _check


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AgencyCreateRequest(BaseModel):
    name: str

class InviteMemberRequest(BaseModel):
    email: str
    role: AgencyRole = AgencyRole.AGENCY_OPERATOR

class UpdateMemberRoleRequest(BaseModel):
    role: AgencyRole

class CreateWorkspaceRequest(BaseModel):
    name: str

class TransferOwnershipRequest(BaseModel):
    owner_type: OwnerType
    owner_user_id: Optional[str] = None
    owner_agency_id: Optional[str] = None


# ─── Serializers ──────────────────────────────────────────────────────────────

def _agency_to_dict(agency: AgencyAccount, member: Optional[AgencyMember] = None) -> dict:
    d = {
        "id": str(agency.id),
        "name": agency.name,
        "status": agency.status.value,
        "owner_user_id": str(agency.owner_user_id),
        "plan_id": str(agency.plan_id) if agency.plan_id else None,
        "created_at": agency.created_at.isoformat(),
    }
    if member:
        d["my_role"] = member.role.value
    return d


def _member_to_dict(member: AgencyMember, user: Optional[User] = None) -> dict:
    d = {
        "id": str(member.id),
        "agency_id": str(member.agency_id),
        "user_id": str(member.user_id),
        "role": member.role.value,
        "created_at": member.created_at.isoformat(),
    }
    if user:
        d["email"] = user.email
        d["full_name"] = user.full_name
    return d


# ─── Endpoints ────────────────────────────────────────────────────────────────

# 1. POST /agency/create — Create a new agency
@router.post("/create", response_model=ResponseEnvelope[dict])
async def create_agency(
    payload: AgencyCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # Check user doesn't already own an agency
    existing = await _get_user_agency(user, db)
    if existing:
        return wrap_error("You already belong to an agency")

    # Create agency
    agency = AgencyAccount(
        name=payload.name,
        owner_user_id=user.id,
    )
    db.add(agency)
    await db.flush()

    # Add creator as AGENCY_OWNER
    member = AgencyMember(
        agency_id=agency.id,
        user_id=user.id,
        role=AgencyRole.AGENCY_OWNER,
    )
    db.add(member)
    await audit_event(
        db, action="agency_create", entity_type="agency",
        entity_id=str(agency.id), actor_user_id=user.id,
        outcome="success", agency_id=agency.id, request=request,
    )
    await db.commit()
    await db.refresh(agency)

    return wrap_data(_agency_to_dict(agency, member))


# 2. GET /agency/me — Agency profile + user's role
@router.get("/me", response_model=ResponseEnvelope[dict])
async def get_my_agency(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    pair = await _get_user_agency(user, db)
    if not pair:
        return wrap_data(None)
    agency, member = pair

    # Get workspace count
    ws_count_res = await db.execute(
        select(func.count(WorkspaceOwnership.id)).where(
            WorkspaceOwnership.owner_agency_id == agency.id
        )
    )
    ws_count = ws_count_res.scalar_one() or 0

    # Get member count
    mem_count_res = await db.execute(
        select(func.count(AgencyMember.id)).where(
            AgencyMember.agency_id == agency.id
        )
    )
    mem_count = mem_count_res.scalar_one() or 0

    # Get max_workspaces limit from plan
    max_ws = None
    if agency.plan_id:
        ent_res = await db.execute(
            select(PlanEntitlement).where(
                PlanEntitlement.plan_id == agency.plan_id,
                PlanEntitlement.module_key == "max_workspaces",
            )
        )
        ent = ent_res.scalars().first()
        if ent:
            max_ws = ent.hard_limit

    data = _agency_to_dict(agency, member)
    data["workspace_count"] = ws_count
    data["member_count"] = mem_count
    data["max_workspaces"] = max_ws
    return wrap_data(data)


# 3. GET /agency/members — List agency members
@router.get("/members", response_model=ResponseEnvelope[dict])
async def list_agency_members(
    auth: tuple = Depends(require_agency_role([
        AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN,
        AgencyRole.AGENCY_OPERATOR, AgencyRole.AGENCY_VIEWER,
    ])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _, _ = auth

    result = await db.execute(
        select(AgencyMember, User)
        .join(User, User.id == AgencyMember.user_id)
        .where(AgencyMember.agency_id == agency.id)
        .order_by(AgencyMember.created_at)
    )
    rows = result.all()

    return wrap_data({
        "items": [_member_to_dict(m, u) for m, u in rows],
        "total": len(rows),
    })


# 4. POST /agency/members/invite — Invite user by email
@router.post("/members/invite", response_model=ResponseEnvelope[dict])
async def invite_agency_member(
    payload: InviteMemberRequest,
    request: Request,
    auth: tuple = Depends(require_agency_role([AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _, acting_user = auth

    # Find or fail user
    user_res = await db.execute(select(User).where(User.email == payload.email))
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="No user found with that email")

    # Check not already a member
    existing_res = await db.execute(
        select(AgencyMember).where(
            AgencyMember.agency_id == agency.id,
            AgencyMember.user_id == target_user.id,
        )
    )
    if existing_res.scalars().first():
        return wrap_error("User is already a member of this agency")

    member = AgencyMember(
        agency_id=agency.id,
        user_id=target_user.id,
        role=payload.role,
    )
    db.add(member)

    # Auto-provision WorkspaceMember rows for all agency-owned workspaces
    ws_role = _AGENCY_ROLE_TO_WORKSPACE_ROLE.get(payload.role, WorkspaceRole.VIEWER)
    ownership_res = await db.execute(
        select(WorkspaceOwnership.workspace_id).where(
            WorkspaceOwnership.owner_agency_id == agency.id
        )
    )
    for row in ownership_res.all():
        ws_id = row[0]
        # Check if membership already exists (shouldn't, but be safe)
        existing_mem = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == target_user.id,
                WorkspaceMember.workspace_id == ws_id,
            )
        )
        if not existing_mem.scalars().first():
            db.add(WorkspaceMember(
                user_id=target_user.id,
                workspace_id=ws_id,
                role=ws_role,
            ))

    await audit_event(
        db, action="agency_member_invite", entity_type="agency_member",
        entity_id=payload.email, actor_user_id=acting_user.id,
        outcome="success", agency_id=agency.id, request=request,
        metadata={"invited_email": payload.email, "role": payload.role.value},
    )
    await db.commit()
    await db.refresh(member)

    return wrap_data(_member_to_dict(member, target_user))


# 5. PATCH /agency/members/{member_id}/role — Update member role
@router.patch("/members/{member_id}/role", response_model=ResponseEnvelope[dict])
async def update_member_role(
    member_id: str,
    payload: UpdateMemberRoleRequest,
    request: Request,
    auth: tuple = Depends(require_agency_role([AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _, acting_user = auth

    target = await db.get(AgencyMember, UUID(member_id))
    if not target or target.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Member not found")

    # Cannot change own role (owners)
    if target.user_id == acting_user.id:
        return wrap_error("Cannot change your own role")

    old_role = target.role
    target.role = payload.role
    await db.commit()
    await db.refresh(target)

    # Update workspace membership roles for agency-owned workspaces
    new_ws_role = _AGENCY_ROLE_TO_WORKSPACE_ROLE.get(payload.role, WorkspaceRole.VIEWER)
    ownership_res = await db.execute(
        select(WorkspaceOwnership.workspace_id).where(
            WorkspaceOwnership.owner_agency_id == agency.id
        )
    )
    for row in ownership_res.all():
        ws_id = row[0]
        mem_res = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == target.user_id,
                WorkspaceMember.workspace_id == ws_id,
            )
        )
        ws_mem = mem_res.scalars().first()
        if ws_mem:
            ws_mem.role = new_ws_role
    await db.commit()

    await audit_event(
        db, action="agency_member_role_change", entity_type="agency_member",
        entity_id=member_id, actor_user_id=acting_user.id,
        outcome="success", agency_id=agency.id, request=request,
        metadata={"old_role": old_role.value, "new_role": payload.role.value},
    )
    await db.commit()
    return wrap_data({
        "id": str(target.id),
        "old_role": old_role.value,
        "new_role": payload.role.value,
    })


# 6. DELETE /agency/members/{member_id} — Remove member
@router.delete("/members/{member_id}", response_model=ResponseEnvelope[dict])
async def remove_agency_member(
    member_id: str,
    request: Request,
    auth: tuple = Depends(require_agency_role([AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _, acting_user = auth

    target = await db.get(AgencyMember, UUID(member_id))
    if not target or target.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Member not found")

    if target.user_id == acting_user.id:
        return wrap_error("Cannot remove yourself from the agency")

    # Remove workspace memberships for agency-owned workspaces
    ownership_res = await db.execute(
        select(WorkspaceOwnership.workspace_id).where(
            WorkspaceOwnership.owner_agency_id == agency.id
        )
    )
    for row in ownership_res.all():
        ws_id = row[0]
        mem_res = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == target.user_id,
                WorkspaceMember.workspace_id == ws_id,
            )
        )
        ws_mem = mem_res.scalars().first()
        if ws_mem:
            await db.delete(ws_mem)

    await db.delete(target)
    await audit_event(
        db, action="agency_member_remove", entity_type="agency_member",
        entity_id=member_id, actor_user_id=acting_user.id,
        outcome="success", agency_id=agency.id, request=request,
    )
    await db.commit()

    return wrap_data({"message": "Member removed", "id": member_id})


# 7. POST /agency/workspaces — Create client workspace (enforces max_workspaces)
@router.post("/workspaces", response_model=ResponseEnvelope[dict])
async def create_agency_workspace(
    payload: CreateWorkspaceRequest,
    request: Request,
    auth: tuple = Depends(require_agency_role([AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _, acting_user = auth

    # Check max_workspaces limit
    if agency.plan_id:
        ent_res = await db.execute(
            select(PlanEntitlement).where(
                PlanEntitlement.plan_id == agency.plan_id,
                PlanEntitlement.module_key == "max_workspaces",
            )
        )
        ent = ent_res.scalars().first()
        if ent and ent.hard_limit is not None:
            current_count_res = await db.execute(
                select(func.count(WorkspaceOwnership.id)).where(
                    WorkspaceOwnership.owner_agency_id == agency.id
                )
            )
            current_count = current_count_res.scalar_one() or 0
            if current_count >= ent.hard_limit:
                raise HTTPException(
                    status_code=403,
                    detail=f"Workspace limit reached ({ent.hard_limit}). Upgrade your plan to create more workspaces.",
                )

    # Create workspace
    workspace = Workspace(name=payload.name)
    db.add(workspace)
    await db.flush()

    # Create ownership record
    ownership = WorkspaceOwnership(
        workspace_id=workspace.id,
        owner_type=OwnerType.AGENCY,
        owner_agency_id=agency.id,
    )
    db.add(ownership)

    # Assign agency plan to workspace (if agency has a plan)
    if agency.plan_id:
        wp = WorkspacePlan(
            workspace_id=workspace.id,
            plan_id=agency.plan_id,
            assigned_by=acting_user.id,
        )
        db.add(wp)
        workspace.subscription_tier = "agency"

    # Create WorkspaceMember rows for all agency members
    members_res = await db.execute(
        select(AgencyMember).where(AgencyMember.agency_id == agency.id)
    )
    for am in members_res.scalars().all():
        ws_role = _AGENCY_ROLE_TO_WORKSPACE_ROLE.get(am.role, WorkspaceRole.VIEWER)
        db.add(WorkspaceMember(
            user_id=am.user_id,
            workspace_id=workspace.id,
            role=ws_role,
        ))

    await audit_event(
        db, action="agency_workspace_create", entity_type="workspace",
        entity_id=str(workspace.id), actor_user_id=acting_user.id,
        outcome="success", agency_id=agency.id, workspace_id=workspace.id,
        request=request,
    )
    await db.commit()
    await db.refresh(workspace)

    return wrap_data({
        "id": str(workspace.id),
        "name": workspace.name,
        "agency_id": str(agency.id),
        "created_at": workspace.created_at.isoformat(),
    })


# 8. GET /agency/workspaces — List agency-owned workspaces
@router.get("/workspaces", response_model=ResponseEnvelope[dict])
async def list_agency_workspaces(
    auth: tuple = Depends(require_agency_role([
        AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN,
        AgencyRole.AGENCY_OPERATOR, AgencyRole.AGENCY_VIEWER,
    ])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _, _ = auth

    result = await db.execute(
        select(Workspace, WorkspaceOwnership)
        .join(WorkspaceOwnership, WorkspaceOwnership.workspace_id == Workspace.id)
        .where(WorkspaceOwnership.owner_agency_id == agency.id)
        .order_by(Workspace.created_at.desc())
    )
    rows = result.all()

    items = []
    for ws, ownership in rows:
        # Get member count per workspace
        mem_res = await db.execute(
            select(func.count(WorkspaceMember.user_id)).where(
                WorkspaceMember.workspace_id == ws.id
            )
        )
        mem_count = mem_res.scalar_one() or 0

        items.append({
            "id": str(ws.id),
            "name": ws.name,
            "subscription_tier": ws.subscription_tier,
            "member_count": mem_count,
            "created_at": ws.created_at.isoformat(),
        })

    return wrap_data({"items": items, "total": len(items)})


# 9. POST /agency/workspaces/{workspace_id}/transfer — Transfer ownership
@router.post("/workspaces/{workspace_id}/transfer", response_model=ResponseEnvelope[dict])
async def transfer_workspace_ownership(
    workspace_id: str,
    payload: TransferOwnershipRequest,
    request: Request,
    auth: tuple = Depends(require_agency_role([AgencyRole.AGENCY_OWNER])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _, acting_user = auth
    ws_uuid = UUID(workspace_id)

    # Verify workspace is owned by this agency
    own_res = await db.execute(
        select(WorkspaceOwnership).where(
            WorkspaceOwnership.workspace_id == ws_uuid,
            WorkspaceOwnership.owner_agency_id == agency.id,
        )
    )
    ownership = own_res.scalars().first()
    if not ownership:
        raise HTTPException(status_code=404, detail="Workspace not found or not owned by this agency")

    if payload.owner_type == OwnerType.USER:
        if not payload.owner_user_id:
            return wrap_error("owner_user_id is required for user ownership transfer")
        target_user = await db.get(User, UUID(payload.owner_user_id))
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        ownership.owner_type = OwnerType.USER
        ownership.owner_user_id = target_user.id
        ownership.owner_agency_id = None
    elif payload.owner_type == OwnerType.AGENCY:
        if not payload.owner_agency_id:
            return wrap_error("owner_agency_id is required for agency ownership transfer")
        target_agency = await db.get(AgencyAccount, UUID(payload.owner_agency_id))
        if not target_agency:
            raise HTTPException(status_code=404, detail="Target agency not found")
        ownership.owner_type = OwnerType.AGENCY
        ownership.owner_agency_id = target_agency.id
        ownership.owner_user_id = None

    await audit_event(
        db, action="agency_ownership_transfer", entity_type="workspace",
        entity_id=workspace_id, actor_user_id=acting_user.id,
        outcome="success", agency_id=agency.id, request=request,
        metadata={"new_owner_type": payload.owner_type.value},
    )
    await db.commit()

    return wrap_data({
        "workspace_id": workspace_id,
        "new_owner_type": payload.owner_type.value,
        "message": "Ownership transferred successfully",
    })


# ─── Agency Settings (Mission 16) ────────────────────────────────────────────

class PatchAgencySettingsRequest(BaseModel):
    settings: dict


@router.get("/settings")
async def get_agency_settings_endpoint(
    auth: tuple = Depends(require_agency_role([
        AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN,
        AgencyRole.AGENCY_OPERATOR, AgencyRole.AGENCY_VIEWER,
    ])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _member, _user = auth
    result = await _get_agency_settings(agency.id, db)
    await db.commit()
    return wrap_data({"settings": result.settings, "version": result.version})


@router.patch("/settings")
async def update_agency_settings_endpoint(
    payload: PatchAgencySettingsRequest,
    auth: tuple = Depends(require_agency_role([
        AgencyRole.AGENCY_OWNER, AgencyRole.AGENCY_ADMIN,
    ])),
    db: AsyncSession = Depends(get_db),
) -> Any:
    agency, _member, acting_user = auth
    result = await _patch_agency_settings(
        agency.id, payload.settings, acting_user.id, db,
    )
    if not result.success:
        return wrap_error(result.error)

    await log_admin_action(
        db, acting_user.id, "update_agency_settings",
        "agency_settings", str(agency.id),
        metadata={"version": result.version, "patch_keys": list(payload.settings.keys())},
    )
    await db.commit()
    return wrap_data({"settings": result.settings, "version": result.version})
