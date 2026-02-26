"""
Mission 16 — Settings System Tests
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    User, Workspace, WorkspaceMember, WorkspaceRole,
    AgencyAccount, AgencyMember, AgencyRole, AgencyStatus,
    AdminAuditLog, WorkspaceSettings, AgencySettings, SystemSettings,
)
from app.core.security import get_password_hash
from app.api.deps import get_current_user
from app.core.db import get_db
from app.services.settings_service import (
    _deep_merge,
    _validate_keys,
    get_workspace_settings,
    patch_workspace_settings,
    get_agency_settings,
    patch_agency_settings,
    get_system_settings,
    patch_system_settings,
    WORKSPACE_SETTINGS_DEFAULT,
    AGENCY_SETTINGS_DEFAULT,
    SYSTEM_SETTINGS_DEFAULT,
)
from main import app


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _create_user(db: AsyncSession, email: str, name: str = "Test User", superuser: bool = False) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("password123"),
        full_name=name,
        is_active=True,
        is_superuser=superuser,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_workspace(db: AsyncSession, user: User, name: str = "Test WS") -> Workspace:
    ws = Workspace(name=name)
    db.add(ws)
    await db.flush()
    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=WorkspaceRole.OWNER)
    db.add(member)
    await db.flush()
    return ws


def _auth_override(user: User):
    async def _override():
        return user
    return _override


def _db_override(db_session: AsyncSession):
    async def _override():
        yield db_session
    return _override


# ─── Service-Level Tests ─────────────────────────────────────────────────────

def test_deep_merge():
    """Test nested dict merge works correctly."""
    base = {"a": {"x": 1, "y": 2}, "b": 10}
    patch = {"a": {"x": 99}, "b": 20}
    result = _deep_merge(base, patch)
    assert result == {"a": {"x": 99, "y": 2}, "b": 20}
    # base not mutated
    assert base["a"]["x"] == 1


def test_deep_merge_ignores_unknown_keys():
    """Deep merge only touches keys present in base."""
    base = {"a": 1}
    patch = {"a": 2, "unknown": 3}
    result = _deep_merge(base, patch)
    assert result == {"a": 2}
    assert "unknown" not in result


def test_validate_keys_rejects_unknown():
    """Validate keys returns invalid paths."""
    schema = {"a": {"x": 1}, "b": 2}
    patch = {"a": {"x": 5, "bad_key": 9}, "c": 3}
    invalid = _validate_keys(patch, schema)
    assert "a.bad_key" in invalid
    assert "c" in invalid
    assert len(invalid) == 2


def test_validate_keys_accepts_valid():
    """Valid partial patches pass validation."""
    schema = WORKSPACE_SETTINGS_DEFAULT
    patch = {"ai": {"temperature": 0.5}, "automation": {"auto_publish": True}}
    invalid = _validate_keys(patch, schema)
    assert invalid == []


@pytest.mark.asyncio
async def test_workspace_settings_lazy_init(db_session: AsyncSession):
    """First GET creates workspace settings with defaults."""
    user = await _create_user(db_session, "ws_settings_init@test.com")
    ws = await _create_workspace(db_session, user)

    result = await get_workspace_settings(ws.id, db_session)
    assert result.success is True
    assert result.version == 1
    assert result.settings["ai"]["temperature"] == 0.7
    assert result.settings["general"]["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_workspace_settings_patch_merges(db_session: AsyncSession):
    """PATCH deep-merges into existing settings."""
    user = await _create_user(db_session, "ws_patch@test.com")
    ws = await _create_workspace(db_session, user)

    # Initialize
    await get_workspace_settings(ws.id, db_session)

    # Patch only ai.temperature
    result = await patch_workspace_settings(
        ws.id, {"ai": {"temperature": 0.3}}, user.id, db_session,
    )
    assert result.success is True
    assert result.settings["ai"]["temperature"] == 0.3
    # Other ai keys preserved
    assert result.settings["ai"]["max_tokens"] == 2048
    assert result.settings["ai"]["guardrails_enabled"] is True
    # Other sections preserved
    assert result.settings["general"]["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_version_increments_on_update(db_session: AsyncSession):
    """Version goes from 1 to 2 on first update."""
    user = await _create_user(db_session, "ws_version@test.com")
    ws = await _create_workspace(db_session, user)

    r1 = await get_workspace_settings(ws.id, db_session)
    assert r1.version == 1

    r2 = await patch_workspace_settings(
        ws.id, {"ai": {"temperature": 0.9}}, user.id, db_session,
    )
    assert r2.version == 2


@pytest.mark.asyncio
async def test_invalid_key_rejected(db_session: AsyncSession):
    """PATCH with unknown key returns error with invalid_keys list."""
    user = await _create_user(db_session, "ws_invalid@test.com")
    ws = await _create_workspace(db_session, user)

    result = await patch_workspace_settings(
        ws.id, {"ai": {"unknown_field": 123}}, user.id, db_session,
    )
    assert result.success is False
    assert "ai.unknown_field" in result.invalid_keys


@pytest.mark.asyncio
async def test_agency_settings_crud(db_session: AsyncSession):
    """Agency settings: lazy init + patch."""
    user = await _create_user(db_session, "ag_settings@test.com")
    agency = AgencyAccount(name="SettingsAgency", owner_user_id=user.id)
    db_session.add(agency)
    await db_session.flush()

    # Lazy init
    r1 = await get_agency_settings(agency.id, db_session)
    assert r1.success is True
    assert r1.version == 1
    assert r1.settings["branding"]["logo_url"] is None

    # Patch
    r2 = await patch_agency_settings(
        agency.id, {"branding": {"primary_color": "#FF0000"}}, user.id, db_session,
    )
    assert r2.success is True
    assert r2.settings["branding"]["primary_color"] == "#FF0000"
    assert r2.version == 2


@pytest.mark.asyncio
async def test_system_settings_crud(db_session: AsyncSession):
    """System settings: lazy init + patch."""
    user = await _create_user(db_session, "sys_settings@test.com", superuser=True)

    r1 = await get_system_settings(db_session)
    assert r1.success is True
    assert r1.settings["maintenance_mode"] is False

    r2 = await patch_system_settings(
        {"maintenance_mode": True}, user.id, db_session,
    )
    assert r2.success is True
    assert r2.settings["maintenance_mode"] is True
    assert r2.version > r1.version


# ─── API-Level Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workspace_settings_requires_owner_for_patch(async_client: AsyncClient, db_session: AsyncSession):
    """Non-owner gets 403 on PATCH."""
    owner = await _create_user(db_session, "ws_owner_rbac@test.com")
    viewer = await _create_user(db_session, "ws_viewer_rbac@test.com")
    ws = await _create_workspace(db_session, owner)

    # Add viewer as VIEWER
    vm = WorkspaceMember(workspace_id=ws.id, user_id=viewer.id, role=WorkspaceRole.VIEWER)
    db_session.add(vm)
    await db_session.flush()

    # Authenticate as viewer
    app.dependency_overrides[get_current_user] = _auth_override(viewer)
    app.dependency_overrides[get_db] = _db_override(db_session)

    res = await async_client.patch(
        "/api/v1/settings/workspace",
        json={"settings": {"ai": {"temperature": 0.1}}},
        headers={"X-Workspace-ID": str(ws.id)},
    )
    assert res.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_audit_log_on_settings_change(async_client: AsyncClient, db_session: AsyncSession):
    """AdminAuditLog row created after workspace settings PATCH."""
    owner = await _create_user(db_session, "ws_audit@test.com")
    ws = await _create_workspace(db_session, owner)

    app.dependency_overrides[get_current_user] = _auth_override(owner)
    app.dependency_overrides[get_db] = _db_override(db_session)

    res = await async_client.patch(
        "/api/v1/settings/workspace",
        json={"settings": {"automation": {"auto_publish": True}}},
        headers={"X-Workspace-ID": str(ws.id)},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Check audit log
    log_result = await db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.action == "update_workspace_settings",
            AdminAuditLog.entity_id == str(ws.id),
        )
    )
    log_entry = log_result.scalars().first()
    assert log_entry is not None
    assert log_entry.actor_user_id == owner.id

    app.dependency_overrides.clear()
