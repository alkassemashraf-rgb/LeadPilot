"""
Mission 34 — Plan Override Tests.

Coverage:
  1. test_override_applies_immediately        — create override → GET /entitlements shows source=override
  2. test_override_expires_via_resolver_self_heal — stale ACTIVE override → resolver marks it expired
  3. test_override_expires_via_worker_task    — expire_plan_overrides_task flips status + writes audit
  4. test_revoke_override_reverts             — POST revoke → effective plan back to base
  5. test_prevent_multiple_active_overrides   — second POST returns wrap_error
  6. test_audit_log_written                   — create + revoke → two AdminAuditLog entries
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    Plan, PlanEntitlement, WorkspacePlan,
    PlanOverride, AdminAuditLog,
    Workspace, WorkspaceMember, User,
    SystemModuleConfig,
)
from app.core import security
from app.core.modules import module_cache


# ── Helpers ──────────────────────────────────────────────────────────────────


def _auth(token: str, workspace_id: Optional[str] = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-ID"] = workspace_id
    return headers


async def _create_superadmin(db: AsyncSession, email: str) -> User:
    admin = User(
        id=uuid4(),
        email=email,
        hashed_password=security.get_password_hash("Admin@pass123"),
        full_name="Test Admin",
        is_active=True,
        is_superuser=True,
        email_verified_at=datetime.utcnow(),
    )
    db.add(admin)
    await db.flush()
    return admin


async def _login_admin(client: AsyncClient, email: str) -> str:
    res = await client.post(
        "/api/v1/admin_auth/login",
        json={"email": email, "password": "Admin@pass123"},
    )
    return res.json()["data"]["access_token"]


async def _signup_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "securepassword123",
        "full_name": "Test User",
    })
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "securepassword123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    return login.json()["data"]["access_token"]


@pytest.fixture(autouse=True)
def clear_module_cache():
    module_cache._cache.clear()
    yield
    module_cache._cache.clear()


@pytest_asyncio.fixture
async def override_setup(async_client: AsyncClient, db_session: AsyncSession):
    """
    Seeds:
      - superadmin user
      - regular user with workspace + member
      - two plans: free (base) and pro (used for override)
      - free plan assigned to workspace
    """
    admin = await _create_superadmin(db_session, "override-admin@test.com")
    admin_token = await _login_admin(async_client, "override-admin@test.com")

    # Regular product user
    product_token = await _signup_and_login(async_client, "override-user@test.com")
    me_res = await async_client.get("/api/v1/auth/me", headers=_auth(product_token))
    user_id = UUID(me_res.json()["data"]["id"])

    # Workspace
    ws = Workspace(id=uuid4(), name="Override WS", subscription_tier="free")
    db_session.add(ws)
    member = WorkspaceMember(user_id=user_id, workspace_id=ws.id, role="owner")
    db_session.add(member)

    # Free plan
    free_plan = Plan(id=uuid4(), name="free_ov_test", display_name="Free Test", is_active=True)
    db_session.add(free_plan)
    db_session.add(PlanEntitlement(plan_id=free_plan.id, module_key="analytics", hard_limit=None))
    wp = WorkspacePlan(workspace_id=ws.id, plan_id=free_plan.id, assigned_by=user_id)
    db_session.add(wp)

    # Pro plan (target for overrides)
    pro_plan = Plan(id=uuid4(), name="pro_ov_test", display_name="Pro Test", is_active=True)
    db_session.add(pro_plan)
    db_session.add(PlanEntitlement(plan_id=pro_plan.id, module_key="analytics", hard_limit=None))
    db_session.add(PlanEntitlement(plan_id=pro_plan.id, module_key="dispatch_engine", hard_limit=None))

    # Enable modules globally
    for mod in ["analytics", "dispatch_engine"]:
        db_session.add(SystemModuleConfig(module_name=mod, is_enabled=True))

    await db_session.flush()

    return {
        "admin_token": admin_token,
        "admin": admin,
        "product_token": product_token,
        "workspace": ws,
        "free_plan": free_plan,
        "pro_plan": pro_plan,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_override_applies_immediately(async_client: AsyncClient, override_setup):
    """Creating an override immediately changes the effective plan returned by GET /entitlements."""
    s = override_setup
    ws_id = str(s["workspace"].id)

    # Before override: plan_source should be "base"
    headers = _auth(s["product_token"], ws_id)
    before = await async_client.get("/api/v1/entitlements", headers=headers)
    assert before.status_code == 200
    plan_before = before.json()["data"]["plan"]
    assert plan_before["plan_source"] in ("base", "free")

    # Create override
    res = await async_client.post(
        f"/api/v1/admin/workspaces/{ws_id}/plan-override",
        json={"plan_id": str(s["pro_plan"].id), "duration_days": 7, "reason": "Test trial"},
        headers=_auth(s["admin_token"]),
    )
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"]["effective"]["plan_source"] == "override"

    # After override: entitlements reflect the pro plan
    after = await async_client.get("/api/v1/entitlements", headers=headers)
    assert after.status_code == 200
    plan_after = after.json()["data"]["plan"]
    assert plan_after["plan_source"] == "override"
    assert plan_after["override_expires_at"] is not None
    assert plan_after["code"] == "pro_ov_test"


@pytest.mark.asyncio
async def test_override_expires_via_resolver_self_heal(async_client: AsyncClient, override_setup, db_session: AsyncSession):
    """A stale ACTIVE override (ends_at in past) is self-healed to EXPIRED by the resolver."""
    s = override_setup
    ws_id = str(s["workspace"].id)

    # Insert a stale override directly with ends_at in the past
    stale = PlanOverride(
        workspace_id=s["workspace"].id,
        plan_id=s["pro_plan"].id,
        starts_at=datetime.utcnow() - timedelta(days=10),
        ends_at=datetime.utcnow() - timedelta(seconds=1),
        status="active",
        reason="stale",
        created_by_admin_id=s["admin"].id,
    )
    db_session.add(stale)
    await db_session.flush()

    # Call GET /entitlements — resolver should self-heal
    res = await async_client.get("/api/v1/entitlements", headers=_auth(s["product_token"], ws_id))
    assert res.status_code == 200
    plan_info = res.json()["data"]["plan"]
    # After self-heal, should fall back to base plan
    assert plan_info["plan_source"] in ("base", "free")

    # The stale override should now be marked expired in DB
    await db_session.refresh(stale)
    assert stale.status == "expired"


@pytest.mark.asyncio
async def test_override_expires_via_worker_task(override_setup, db_session: AsyncSession):
    """_expire_plan_overrides_core marks stale ACTIVE overrides expired and writes audit log."""
    from app.workers.tasks import _expire_plan_overrides_core

    s = override_setup

    # Insert a stale override
    stale = PlanOverride(
        workspace_id=s["workspace"].id,
        plan_id=s["pro_plan"].id,
        starts_at=datetime.utcnow() - timedelta(days=5),
        ends_at=datetime.utcnow() - timedelta(minutes=1),
        status="active",
        reason="worker expiry test",
        created_by_admin_id=s["admin"].id,
    )
    db_session.add(stale)
    await db_session.flush()
    override_id = stale.id

    # Run the core expiry logic directly with the test session
    await _expire_plan_overrides_core(db_session)

    # Verify status is now expired
    await db_session.refresh(stale)
    assert stale.status == "expired"

    # Verify audit log was written
    audit_result = await db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.action == "PLAN_OVERRIDE_EXPIRED",
            AdminAuditLog.entity_id == str(override_id),
        )
    )
    audit_entry = audit_result.scalars().first()
    assert audit_entry is not None
    assert audit_entry.actor_type == "system"


@pytest.mark.asyncio
async def test_revoke_override_reverts(async_client: AsyncClient, override_setup):
    """Revoking an override reverts the effective plan back to base."""
    s = override_setup
    ws_id = str(s["workspace"].id)

    # Create override
    create_res = await async_client.post(
        f"/api/v1/admin/workspaces/{ws_id}/plan-override",
        json={"plan_id": str(s["pro_plan"].id), "duration_days": 14},
        headers=_auth(s["admin_token"]),
    )
    assert create_res.json()["success"] is True

    # Confirm override is active
    ent_res = await async_client.get("/api/v1/entitlements", headers=_auth(s["product_token"], ws_id))
    assert ent_res.json()["data"]["plan"]["plan_source"] == "override"

    # Revoke
    revoke_res = await async_client.post(
        f"/api/v1/admin/workspaces/{ws_id}/plan-override/revoke",
        json={"reason": "Revocation test"},
        headers=_auth(s["admin_token"]),
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["success"] is True
    assert revoke_res.json()["data"]["effective"]["plan_source"] in ("base", "free")

    # Entitlements should now show base plan
    after_res = await async_client.get("/api/v1/entitlements", headers=_auth(s["product_token"], ws_id))
    assert after_res.json()["data"]["plan"]["plan_source"] in ("base", "free")
    assert after_res.json()["data"]["plan"]["code"] == "free_ov_test"


@pytest.mark.asyncio
async def test_prevent_multiple_active_overrides(async_client: AsyncClient, override_setup):
    """Creating a second override while one is active returns a wrap_error (success=False)."""
    s = override_setup
    ws_id = str(s["workspace"].id)

    # First override
    first = await async_client.post(
        f"/api/v1/admin/workspaces/{ws_id}/plan-override",
        json={"plan_id": str(s["pro_plan"].id), "duration_days": 7},
        headers=_auth(s["admin_token"]),
    )
    assert first.json()["success"] is True

    # Second override attempt — should return wrap_error
    second = await async_client.post(
        f"/api/v1/admin/workspaces/{ws_id}/plan-override",
        json={"plan_id": str(s["pro_plan"].id), "duration_days": 3},
        headers=_auth(s["admin_token"]),
    )
    assert second.status_code == 200
    assert second.json()["success"] is False
    assert "active" in second.json()["error"].lower()


@pytest.mark.asyncio
async def test_audit_log_written(async_client: AsyncClient, override_setup, db_session: AsyncSession):
    """Creating and revoking an override each produce an AdminAuditLog entry."""
    s = override_setup
    ws_id = str(s["workspace"].id)

    # Create
    await async_client.post(
        f"/api/v1/admin/workspaces/{ws_id}/plan-override",
        json={"plan_id": str(s["pro_plan"].id), "duration_days": 10, "reason": "Audit test"},
        headers=_auth(s["admin_token"]),
    )

    # Revoke
    await async_client.post(
        f"/api/v1/admin/workspaces/{ws_id}/plan-override/revoke",
        json={"reason": "Audit test revoke"},
        headers=_auth(s["admin_token"]),
    )

    # Verify both audit entries exist
    result = await db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.workspace_id == s["workspace"].id,
            AdminAuditLog.action.in_(["PLAN_OVERRIDE_CREATED", "PLAN_OVERRIDE_REVOKED"]),
        )
    )
    entries = result.scalars().all()
    actions = {e.action for e in entries}
    assert "PLAN_OVERRIDE_CREATED" in actions
    assert "PLAN_OVERRIDE_REVOKED" in actions
