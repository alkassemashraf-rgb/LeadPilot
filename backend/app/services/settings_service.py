"""
Settings service — Mission 16

Three-tier settings:
  1. WorkspaceSettings  — per-workspace operational config
  2. AgencySettings     — per-agency branding and defaults
  3. SystemSettings     — single-row admin-level global config

All settings are lazily initialized on first GET, versioned (version++
on every update), validated against canonical schemas (unknown keys
rejected), and deep-merged on PATCH.
"""

import copy
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    WorkspaceSettings,
    AgencySettings,
    SystemSettings,
)

logger = logging.getLogger(__name__)

# ─── Canonical Default Schemas ────────────────────────────────────────────────

WORKSPACE_SETTINGS_DEFAULT: Dict[str, Any] = {
    "general": {
        "name_override": None,
        "logo_url": None,
        "timezone": "UTC",
        "default_language": "en",
    },
    "messaging": {
        "default_reply_delay_seconds": 0,
        "fallback_message_enabled": False,
        "auto_retry_failed_dispatch": True,
    },
    "ai": {
        "default_model": "gemini-1.5-pro",
        "temperature": 0.7,
        "max_tokens": 2048,
        "guardrails_enabled": True,
    },
    "automation": {
        "auto_publish": False,
        "draft_expiry_days": 30,
    },
    "notifications": {
        "email_notifications_enabled": True,
        "webhook_url": None,
    },
}

AGENCY_SETTINGS_DEFAULT: Dict[str, Any] = {
    "branding": {
        "logo_url": None,
        "primary_color": None,
    },
    "defaults": {
        "default_workspace_plan": "starter",
        "default_ai_model": "gemini-1.5-pro",
    },
    "limits_override": {
        "max_workspaces_override": None,
    },
    "notifications": {
        "agency_alert_email": None,
    },
}

SYSTEM_SETTINGS_DEFAULT: Dict[str, Any] = {
    "global_modules": {
        "ai_chat": True,
        "email_engine": True,
        "automation_runtime": True,
        "dispatch": True,
        "integrations": True,
    },
    "defaults": {
        "default_workspace_plan": "starter",
    },
    "maintenance_mode": False,
    "ai_provider_priority": ["gemini"],
}


# ─── Result Dataclass ─────────────────────────────────────────────────────────

@dataclass
class SettingsResult:
    success: bool
    settings: Optional[Dict[str, Any]] = None
    version: Optional[int] = None
    error: Optional[str] = None
    invalid_keys: Optional[List[str]] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge *patch* into *base*. Returns a new dict (base is not mutated)."""
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        elif key in result:
            result[key] = value
    return result


def _validate_keys(
    patch: Dict[str, Any], schema: Dict[str, Any], path: str = ""
) -> List[str]:
    """Return a list of invalid key paths present in *patch* but not in *schema*."""
    invalid: List[str] = []
    for key, value in patch.items():
        full_path = f"{path}.{key}" if path else key
        if key not in schema:
            invalid.append(full_path)
        elif isinstance(value, dict) and isinstance(schema[key], dict):
            invalid.extend(_validate_keys(value, schema[key], full_path))
    return invalid


# ─── Workspace Settings ──────────────────────────────────────────────────────

async def get_workspace_settings(
    workspace_id: UUID, db: AsyncSession
) -> SettingsResult:
    """Get or lazily create workspace settings."""
    result = await db.execute(
        select(WorkspaceSettings).where(
            WorkspaceSettings.workspace_id == workspace_id
        )
    )
    ws = result.scalars().first()
    if not ws:
        ws = WorkspaceSettings(
            workspace_id=workspace_id,
            settings_json=copy.deepcopy(WORKSPACE_SETTINGS_DEFAULT),
            version=1,
        )
        db.add(ws)
        await db.flush()
    return SettingsResult(success=True, settings=ws.settings_json, version=ws.version)


async def patch_workspace_settings(
    workspace_id: UUID,
    patch: Dict[str, Any],
    user_id: UUID,
    db: AsyncSession,
) -> SettingsResult:
    """Validate, deep-merge, and save workspace settings."""
    invalid = _validate_keys(patch, WORKSPACE_SETTINGS_DEFAULT)
    if invalid:
        return SettingsResult(
            success=False,
            error=f"Unknown settings keys: {', '.join(invalid)}",
            invalid_keys=invalid,
        )

    result = await db.execute(
        select(WorkspaceSettings).where(
            WorkspaceSettings.workspace_id == workspace_id
        )
    )
    ws = result.scalars().first()
    if not ws:
        ws = WorkspaceSettings(
            workspace_id=workspace_id,
            settings_json=copy.deepcopy(WORKSPACE_SETTINGS_DEFAULT),
            version=0,
        )
        db.add(ws)
        await db.flush()

    ws.settings_json = _deep_merge(ws.settings_json, patch)
    ws.version += 1
    ws.updated_by_user_id = user_id
    ws.updated_at = datetime.utcnow()
    await db.flush()
    return SettingsResult(success=True, settings=ws.settings_json, version=ws.version)


# ─── Agency Settings ─────────────────────────────────────────────────────────

async def get_agency_settings(
    agency_id: UUID, db: AsyncSession
) -> SettingsResult:
    """Get or lazily create agency settings."""
    result = await db.execute(
        select(AgencySettings).where(AgencySettings.agency_id == agency_id)
    )
    ag = result.scalars().first()
    if not ag:
        ag = AgencySettings(
            agency_id=agency_id,
            settings_json=copy.deepcopy(AGENCY_SETTINGS_DEFAULT),
            version=1,
        )
        db.add(ag)
        await db.flush()
    return SettingsResult(success=True, settings=ag.settings_json, version=ag.version)


async def patch_agency_settings(
    agency_id: UUID,
    patch: Dict[str, Any],
    user_id: UUID,
    db: AsyncSession,
) -> SettingsResult:
    """Validate, deep-merge, and save agency settings."""
    invalid = _validate_keys(patch, AGENCY_SETTINGS_DEFAULT)
    if invalid:
        return SettingsResult(
            success=False,
            error=f"Unknown settings keys: {', '.join(invalid)}",
            invalid_keys=invalid,
        )

    result = await db.execute(
        select(AgencySettings).where(AgencySettings.agency_id == agency_id)
    )
    ag = result.scalars().first()
    if not ag:
        ag = AgencySettings(
            agency_id=agency_id,
            settings_json=copy.deepcopy(AGENCY_SETTINGS_DEFAULT),
            version=0,
        )
        db.add(ag)
        await db.flush()

    ag.settings_json = _deep_merge(ag.settings_json, patch)
    ag.version += 1
    ag.updated_by_user_id = user_id
    ag.updated_at = datetime.utcnow()
    await db.flush()
    return SettingsResult(success=True, settings=ag.settings_json, version=ag.version)


# ─── System Settings ─────────────────────────────────────────────────────────

async def get_system_settings(db: AsyncSession) -> SettingsResult:
    """Get or lazily create the single-row system settings."""
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.singleton_key == "global")
    )
    ss = result.scalars().first()
    if not ss:
        ss = SystemSettings(
            singleton_key="global",
            settings_json=copy.deepcopy(SYSTEM_SETTINGS_DEFAULT),
            version=1,
        )
        db.add(ss)
        await db.flush()
    return SettingsResult(success=True, settings=ss.settings_json, version=ss.version)


async def patch_system_settings(
    patch: Dict[str, Any],
    user_id: UUID,
    db: AsyncSession,
) -> SettingsResult:
    """Validate, deep-merge, and save system settings."""
    invalid = _validate_keys(patch, SYSTEM_SETTINGS_DEFAULT)
    if invalid:
        return SettingsResult(
            success=False,
            error=f"Unknown settings keys: {', '.join(invalid)}",
            invalid_keys=invalid,
        )

    result = await db.execute(
        select(SystemSettings).where(SystemSettings.singleton_key == "global")
    )
    ss = result.scalars().first()
    if not ss:
        ss = SystemSettings(
            singleton_key="global",
            settings_json=copy.deepcopy(SYSTEM_SETTINGS_DEFAULT),
            version=0,
        )
        db.add(ss)
        await db.flush()

    ss.settings_json = _deep_merge(ss.settings_json, patch)
    ss.version += 1
    ss.updated_by_user_id = user_id
    ss.updated_at = datetime.utcnow()
    await db.flush()

    # Bust maintenance mode cache
    _maintenance_cache.clear()

    return SettingsResult(success=True, settings=ss.settings_json, version=ss.version)


# ─── Convenience Accessors ───────────────────────────────────────────────────

async def get_workspace_ai_settings(
    workspace_id: UUID, db: AsyncSession
) -> Dict[str, Any]:
    """Return the 'ai' section for a workspace, with defaults as fallback."""
    result = await get_workspace_settings(workspace_id, db)
    return result.settings.get("ai", WORKSPACE_SETTINGS_DEFAULT["ai"])


async def get_workspace_messaging_settings(
    workspace_id: UUID, db: AsyncSession
) -> Dict[str, Any]:
    """Return the 'messaging' section for a workspace."""
    result = await get_workspace_settings(workspace_id, db)
    return result.settings.get("messaging", WORKSPACE_SETTINGS_DEFAULT["messaging"])


# ─── Maintenance Mode (cached) ──────────────────────────────────────────────

_maintenance_cache: Dict[str, Tuple[float, bool]] = {}
_MAINTENANCE_CACHE_TTL = 15  # seconds

async def is_maintenance_mode(db: AsyncSession) -> bool:
    """Check if system is in maintenance mode. Cached for 15s."""
    cache_key = "maintenance_mode"
    now = time.time()
    if cache_key in _maintenance_cache:
        ts, val = _maintenance_cache[cache_key]
        if now - ts < _MAINTENANCE_CACHE_TTL:
            return val

    result = await get_system_settings(db)
    val = result.settings.get("maintenance_mode", False)
    _maintenance_cache[cache_key] = (now, val)
    return val
