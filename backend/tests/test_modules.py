"""
Part E: Module Toggle Tests — Mission 11
Tests:
  1. test_module_toggle_updates_db_and_audit_log
  2. test_module_disabled_blocks_endpoint_with_envelope
  3. test_admin_portal_module_locked
  4. test_worker_respects_module_disable (via check_module_enabled)
  5. test_frontend_flag_fetch_contract (GET /admin/modules response shape contract)
  6. test_audit_redaction_never_leaks_secrets (unit test, no HTTP)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from unittest.mock import patch

from app.models.models import SystemModuleConfig, AdminAuditLog, User, Workspace
from app.core.modules import (
    module_cache, check_module_enabled,
    MODULE_PROMPT_STUDIO, MODULE_ADMIN_PORTAL, MODULE_DISPATCH_ENGINE,
)
from app.core.audit import redact_metadata


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _superadmin_user() -> User:
    return User(
        email="superadmin@test.com",
        hashed_password="x",
        full_name="Super Admin",
        is_active=True,
        is_superuser=True,
    )


def _regular_user() -> User:
    return User(
        email="user@test.com",
        hashed_password="x",
        full_name="Regular User",
        is_active=True,
        is_superuser=False,
    )


def _workspace() -> Workspace:
    return Workspace(name="Test WS", slug="test-ws")


# ─────────────────────────────────────────────────────────────────────────────
# 1. test_module_toggle_updates_db_and_audit_log
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_module_toggle_updates_db_and_audit_log(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    PATCH /admin/modules/prompt_studio {enabled: false} must:
    - Update SystemModuleConfig.is_enabled to False in DB
    - Write an AdminAuditLog row with action='module_toggle'
    - Return success ResponseEnvelope with is_enabled: false
    """
    from main import app
    from app.api.deps import get_current_user

    admin = _superadmin_user()
    db_session.add(admin)
    await db_session.flush()

    mod = SystemModuleConfig(module_name=MODULE_PROMPT_STUDIO, is_enabled=True)
    db_session.add(mod)
    await db_session.flush()
    module_cache.invalidate(MODULE_PROMPT_STUDIO)

    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = await async_client.patch(
            "/api/v1/admin/modules/prompt_studio",
            json={"enabled": False},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_enabled"] is False
        assert data["data"]["module_name"] == "prompt_studio"

        # Verify DB updated
        result = await db_session.execute(
            select(SystemModuleConfig).where(SystemModuleConfig.module_name == MODULE_PROMPT_STUDIO)
        )
        db_mod = result.scalars().first()
        assert db_mod is not None
        assert db_mod.is_enabled is False

        # Verify audit log written
        audit_result = await db_session.execute(
            select(AdminAuditLog).where(
                AdminAuditLog.action == "module_toggle",
                AdminAuditLog.entity_id == "prompt_studio",
            )
        )
        audit = audit_result.scalars().first()
        assert audit is not None
        assert audit.metadata_json["new_state"] is False
        assert audit.metadata_json["previous_state"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        module_cache.invalidate(MODULE_PROMPT_STUDIO)


# ─────────────────────────────────────────────────────────────────────────────
# 2. test_module_disabled_blocks_endpoint_with_envelope
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_module_disabled_blocks_endpoint_with_envelope(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    When MODULE_PROMPT_STUDIO is disabled, GET /prompt-config/ must return
    HTTP 403 with a ResponseEnvelope containing error text mentioning MODULE_DISABLED.
    """
    from main import app
    from app.api.deps import get_active_workspace, get_current_user

    mod = SystemModuleConfig(module_name=MODULE_PROMPT_STUDIO, is_enabled=False)
    db_session.add(mod)
    await db_session.flush()
    module_cache.invalidate(MODULE_PROMPT_STUDIO)

    ws = _workspace()
    db_session.add(ws)
    user = _regular_user()
    db_session.add(user)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_active_workspace] = lambda: ws

    try:
        response = await async_client.get("/api/v1/prompt-config/")
        assert response.status_code == 403

        data = response.json()
        raw = str(data)
        assert "MODULE_DISABLED" in raw, f"Expected MODULE_DISABLED in response, got: {raw}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_active_workspace, None)
        module_cache.invalidate(MODULE_PROMPT_STUDIO)


# ─────────────────────────────────────────────────────────────────────────────
# 3. test_admin_portal_module_locked
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_portal_module_locked(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    PATCH /admin/modules/admin_portal {enabled: false} must return 400 MODULE_LOCKED.
    The admin_portal module must NEVER be disableable via the API.
    """
    from main import app
    from app.api.deps import get_current_user

    admin = _superadmin_user()
    admin.email = "lock_test_admin@test.com"
    db_session.add(admin)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = await async_client.patch(
            "/api/v1/admin/modules/admin_portal",
            json={"enabled": False},
        )
        assert response.status_code == 400, response.text
        raw = str(response.json())
        assert "MODULE_LOCKED" in raw, f"Expected MODULE_LOCKED in response, got: {raw}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# 4. test_worker_respects_module_disable
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_worker_respects_module_disable(db_session: AsyncSession):
    """
    check_module_enabled() must return False when module is disabled in DB,
    and True when re-enabled. This is the same check Celery workers use.
    """
    mod = SystemModuleConfig(module_name=MODULE_DISPATCH_ENGINE, is_enabled=False)
    db_session.add(mod)
    await db_session.flush()
    module_cache.invalidate(MODULE_DISPATCH_ENGINE)

    result = await check_module_enabled(MODULE_DISPATCH_ENGINE, db_session)
    assert result is False, "Disabled module should return False"

    mod.is_enabled = True
    db_session.add(mod)
    await db_session.flush()
    module_cache.invalidate(MODULE_DISPATCH_ENGINE)

    result = await check_module_enabled(MODULE_DISPATCH_ENGINE, db_session)
    assert result is True, "Re-enabled module should return True"

    module_cache.invalidate(MODULE_DISPATCH_ENGINE)


# ─────────────────────────────────────────────────────────────────────────────
# 5. test_frontend_flag_fetch_contract
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_frontend_flag_fetch_contract(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    GET /admin/modules must return ResponseEnvelope with data as a list, each item
    having 'module_name' (str) and 'is_enabled' (bool). This is the API contract
    that admin-api.ts on the frontend relies on.
    """
    from main import app
    from app.api.deps import get_current_user

    admin = _superadmin_user()
    admin.email = "contract_admin@test.com"
    db_session.add(admin)
    await db_session.flush()

    # Seed a couple of modules with known states
    for name, enabled in [("auth", True), ("email_engine", False)]:
        mod = SystemModuleConfig(module_name=name, is_enabled=enabled)
        db_session.add(mod)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = await async_client.get("/api/v1/admin/modules")
        assert response.status_code == 200, response.text

        data = response.json()
        assert data["success"] is True
        items = data["data"]
        assert isinstance(items, list)
        assert len(items) > 0

        # Verify each item has the required keys and correct types
        for item in items:
            assert "module_name" in item, f"Missing module_name in {item}"
            assert "is_enabled" in item, f"Missing is_enabled in {item}"
            assert isinstance(item["module_name"], str)
            assert isinstance(item["is_enabled"], bool)

        # Verify our seeded values are present and correct
        module_map = {item["module_name"]: item["is_enabled"] for item in items}
        assert module_map.get("auth") is True
        assert module_map.get("email_engine") is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# 6. test_audit_redaction_never_leaks_secrets  (pure unit test — no DB/HTTP)
# ─────────────────────────────────────────────────────────────────────────────

def test_audit_redaction_never_leaks_secrets():
    """
    redact_metadata() must scrub any field whose key contains a sensitive term,
    must handle nested dicts and lists, and must NOT mutate the original dict.
    """
    original = {
        "module_name": "zoho_sync",
        "access_token": "super-secret-oauth-token",
        "api_key": "sk-1234567890",
        "nested": {
            "password": "hunter2",
            "client_secret": "very-secret",
        },
        "items": [
            {"idempotency_key": "idem-abc123", "safe_field": "visible"},
        ],
        "safe_top_level": "I am visible",
    }

    result = redact_metadata(original)

    # Sensitive leaf values must be replaced
    assert result["access_token"] == "***REDACTED***"
    assert result["api_key"] == "***REDACTED***"
    assert result["nested"]["password"] == "***REDACTED***"
    assert result["nested"]["client_secret"] == "***REDACTED***"
    assert result["items"][0]["idempotency_key"] == "***REDACTED***"

    # Safe values must remain intact
    assert result["module_name"] == "zoho_sync"
    assert result["safe_top_level"] == "I am visible"
    assert result["items"][0]["safe_field"] == "visible"

    # The original dict must NOT have been mutated (deep copy guarantee)
    assert original["access_token"] == "super-secret-oauth-token"
    assert original["nested"]["password"] == "hunter2"
