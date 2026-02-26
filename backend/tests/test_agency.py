"""
Mission 15 — Agency Model Tests
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID

from app.models.models import (
    User, Workspace, WorkspaceMember, WorkspaceRole,
    AgencyAccount, AgencyMember, AgencyRole, AgencyStatus,
    WorkspaceOwnership, OwnerType,
    Plan, PlanEntitlement, WorkspacePlan,
)
from app.core.security import get_password_hash
from app.api.deps import get_current_user
from app.core.db import get_db
from main import app


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _create_user(db: AsyncSession, email: str, name: str = "Test User") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("password123"),
        full_name=name,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_plan_with_limit(db: AsyncSession, name: str, max_ws: int) -> Plan:
    plan = Plan(name=name, display_name=name.title(), is_active=True, sort_order=0)
    db.add(plan)
    await db.flush()
    ent = PlanEntitlement(plan_id=plan.id, module_key="max_workspaces", hard_limit=max_ws)
    db.add(ent)
    await db.flush()
    return plan


def _auth_override(user: User):
    """Return a dependency override for get_current_user."""
    async def _override():
        return user
    return _override


def _db_override(db_session: AsyncSession):
    async def _override():
        yield db_session
    return _override


# ─── Test 1: Create agency + GET /agency/me ──────────────────────────────────

@pytest.mark.asyncio
async def test_agency_create_and_me(async_client: AsyncClient, db_session: AsyncSession):
    owner = await _create_user(db_session, "agency_owner@test.com", "Agency Owner")
    await db_session.flush()

    app.dependency_overrides[get_current_user] = _auth_override(owner)
    app.dependency_overrides[get_db] = _db_override(db_session)

    # Create agency
    res = await async_client.post("/api/v1/agency/create", json={"name": "Test Agency"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Test Agency"
    assert data["data"]["my_role"] == "agency_owner"
    agency_id = data["data"]["id"]

    # GET /agency/me
    res2 = await async_client.get("/api/v1/agency/me")
    assert res2.status_code == 200
    me_data = res2.json()["data"]
    assert me_data["id"] == agency_id
    assert me_data["workspace_count"] == 0
    assert me_data["member_count"] == 1

    app.dependency_overrides.clear()


# ─── Test 2: Invite member + role update ─────────────────────────────────────

@pytest.mark.asyncio
async def test_agency_invite_and_role_update(async_client: AsyncClient, db_session: AsyncSession):
    owner = await _create_user(db_session, "inv_owner@test.com", "Inv Owner")
    operator = await _create_user(db_session, "inv_operator@test.com", "Inv Operator")
    await db_session.flush()

    app.dependency_overrides[get_current_user] = _auth_override(owner)
    app.dependency_overrides[get_db] = _db_override(db_session)

    # Create agency
    await async_client.post("/api/v1/agency/create", json={"name": "Invite Test Agency"})

    # Invite operator
    inv_res = await async_client.post("/api/v1/agency/members/invite", json={
        "email": "inv_operator@test.com",
        "role": "agency_operator",
    })
    assert inv_res.status_code == 200
    inv_data = inv_res.json()["data"]
    assert inv_data["role"] == "agency_operator"
    member_id = inv_data["id"]

    # Update role to admin
    role_res = await async_client.patch(f"/api/v1/agency/members/{member_id}/role", json={
        "role": "agency_admin",
    })
    assert role_res.status_code == 200
    assert role_res.json()["data"]["new_role"] == "agency_admin"

    app.dependency_overrides.clear()


# ─── Test 3: Create workspace → ownership + membership ──────────────────────

@pytest.mark.asyncio
async def test_agency_workspace_creates_ownership_and_membership(
    async_client: AsyncClient, db_session: AsyncSession
):
    owner = await _create_user(db_session, "ws_owner@test.com", "WS Owner")
    await db_session.flush()

    app.dependency_overrides[get_current_user] = _auth_override(owner)
    app.dependency_overrides[get_db] = _db_override(db_session)

    # Create agency
    await async_client.post("/api/v1/agency/create", json={"name": "WS Test Agency"})

    # Create workspace
    ws_res = await async_client.post("/api/v1/agency/workspaces", json={"name": "Client WS"})
    assert ws_res.status_code == 200
    ws_data = ws_res.json()["data"]
    ws_id = UUID(ws_data["id"])

    # Verify WorkspaceOwnership
    own_res = await db_session.execute(
        select(WorkspaceOwnership).where(WorkspaceOwnership.workspace_id == ws_id)
    )
    ownership = own_res.scalars().first()
    assert ownership is not None
    assert ownership.owner_type == OwnerType.AGENCY

    # Verify WorkspaceMember created for owner
    mem_res = await db_session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == owner.id,
        )
    )
    membership = mem_res.scalars().first()
    assert membership is not None
    assert membership.role == WorkspaceRole.OWNER

    app.dependency_overrides.clear()


# ─── Test 4: max_workspaces limit enforced ───────────────────────────────────

@pytest.mark.asyncio
async def test_max_workspaces_limit_enforced(async_client: AsyncClient, db_session: AsyncSession):
    owner = await _create_user(db_session, "limit_owner@test.com", "Limit Owner")
    plan = await _create_plan_with_limit(db_session, "test_limit_plan", max_ws=1)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = _auth_override(owner)
    app.dependency_overrides[get_db] = _db_override(db_session)

    # Create agency
    create_res = await async_client.post("/api/v1/agency/create", json={"name": "Limit Agency"})
    agency_id = create_res.json()["data"]["id"]

    # Assign plan to agency directly in DB
    agency = await db_session.get(AgencyAccount, UUID(agency_id))
    agency.plan_id = plan.id
    await db_session.flush()

    # First workspace — should succeed
    ws1 = await async_client.post("/api/v1/agency/workspaces", json={"name": "WS 1"})
    assert ws1.status_code == 200

    # Second workspace — should fail (limit is 1)
    ws2 = await async_client.post("/api/v1/agency/workspaces", json={"name": "WS 2"})
    assert ws2.status_code == 403

    app.dependency_overrides.clear()


# ─── Test 5: Agency member can access owned workspace ────────────────────────

@pytest.mark.asyncio
async def test_agency_member_accesses_workspace(async_client: AsyncClient, db_session: AsyncSession):
    owner = await _create_user(db_session, "access_owner@test.com", "Access Owner")
    await db_session.flush()

    app.dependency_overrides[get_current_user] = _auth_override(owner)
    app.dependency_overrides[get_db] = _db_override(db_session)

    # Create agency + workspace
    await async_client.post("/api/v1/agency/create", json={"name": "Access Agency"})
    ws_res = await async_client.post("/api/v1/agency/workspaces", json={"name": "Access WS"})
    ws_id = ws_res.json()["data"]["id"]

    # List workspaces
    list_res = await async_client.get("/api/v1/agency/workspaces")
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) >= 1
    assert any(ws["id"] == ws_id for ws in items)

    # Access workspace-scoped endpoint with X-Workspace-ID
    members_res = await async_client.get(
        "/api/v1/workspaces/members",
        headers={"X-Workspace-ID": ws_id}
    )
    assert members_res.status_code == 200

    app.dependency_overrides.clear()


# ─── Test 6: Admin can suspend agency ────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_suspend_agency(async_client: AsyncClient, db_session: AsyncSession):
    owner = await _create_user(db_session, "susp_owner@test.com", "Susp Owner")
    admin = await _create_user(db_session, "susp_admin@test.com", "Susp Admin")
    admin.is_superuser = True
    await db_session.flush()

    # Create agency as owner
    app.dependency_overrides[get_current_user] = _auth_override(owner)
    app.dependency_overrides[get_db] = _db_override(db_session)

    create_res = await async_client.post("/api/v1/agency/create", json={"name": "Suspend Agency"})
    agency_id = create_res.json()["data"]["id"]

    # Switch to admin
    app.dependency_overrides[get_current_user] = _auth_override(admin)

    # Suspend
    susp_res = await async_client.patch(
        f"/api/v1/admin/agencies/{agency_id}/status",
        json={"status": "suspended"},
    )
    assert susp_res.status_code == 200
    assert susp_res.json()["data"]["new_status"] == "suspended"

    # Verify agency is suspended
    detail_res = await async_client.get(f"/api/v1/admin/agencies/{agency_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["status"] == "suspended"

    # Switch back to owner — agency endpoints should reject (suspended)
    app.dependency_overrides[get_current_user] = _auth_override(owner)
    ws_res = await async_client.post("/api/v1/agency/workspaces", json={"name": "Blocked WS"})
    assert ws_res.status_code == 403

    app.dependency_overrides.clear()
