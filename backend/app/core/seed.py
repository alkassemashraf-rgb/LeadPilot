"""
Startup seed utilities: Ensures all canonical modules and default plans exist.
Runs once on app startup; idempotent (uses INSERT or IGNORE logic via get-or-create).
"""
import logging
from app.core.db import SessionLocal as AsyncSessionLocal
from app.models.models import SystemModuleConfig, Plan, PlanEntitlement, SystemSettings
from app.core.modules import ALL_MODULES, MODULE_ADMIN_PORTAL
from sqlmodel import select

logger = logging.getLogger(__name__)

# --- Default plan definitions ---
# Each entry: (name, display_name, sort_order, description, entitlements_dict)
# entitlements_dict: {module_key: hard_limit} where None = unlimited
DEFAULT_PLANS = [
    (
        "free", "Free", 0, "Basic access with limited usage",
        {
            "prompt_studio": 1,
            "runtime_engine": 50,
            "integrations_connect": 1,
            "automations": 2,
            "dispatch_engine": 200,
            "knowledge_files": 5,
            "analytics": None,
            "inbox": None,
            "max_workspaces": 1,
        }
    ),
    (
        "growth", "Growth", 1, "Expanded limits for growing teams",
        {
            "prompt_studio": 10,
            "runtime_engine": 500,
            "integrations_connect": 5,
            "automations": 20,
            "dispatch_engine": 2000,
            "knowledge_files": 50,
            "analytics": None,
            "inbox": None,
            "webhooks_ingestion": None,
            "zoho_sync": 500,
            "max_workspaces": 5,
        }
    ),
    (
        "enterprise", "Enterprise", 2, "Unlimited access to all modules",
        {
            "prompt_studio": None,
            "runtime_engine": None,
            "integrations_connect": None,
            "automations": None,
            "dispatch_engine": None,
            "knowledge_files": None,
            "analytics": None,
            "inbox": None,
            "webhooks_ingestion": None,
            "zoho_sync": None,
            "diagnostics": None,
            "email_engine": None,
            "email_verification": None,
            "integrations_hub": None,
            "admin_portal": None,
            "auth": None,
            "max_workspaces": None,
        }
    ),
]


async def seed_modules():
    """
    Ensures every module in ALL_MODULES has a row in systemmoduleconfig.
    - All modules default to is_enabled=True.
    - admin_portal is also enabled by default (and is locked against being disabled via API).
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SystemModuleConfig.module_name))
            existing = {row[0] for row in result.all()}

            new_count = 0
            for module_name in ALL_MODULES:
                if module_name not in existing:
                    mod = SystemModuleConfig(
                        module_name=module_name,
                        is_enabled=True,  # All modules start enabled
                    )
                    db.add(mod)
                    new_count += 1

            if new_count > 0:
                await db.commit()
                logger.info(f"[seed_modules] Seeded {new_count} module(s) into SystemModuleConfig.")
            else:
                logger.info("[seed_modules] All modules already seeded; no action taken.")
    except Exception as e:
        logger.error(f"[seed_modules] Failed to seed modules: {e}", exc_info=True)


async def seed_plans():
    """
    Ensures the default plans (Free, Growth, Enterprise) exist with their entitlements.
    Idempotent: skips plans that already exist by name.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Plan.name))
            existing_plans = {row[0] for row in result.all()}

            new_count = 0
            for name, display_name, sort_order, description, entitlements in DEFAULT_PLANS:
                if name in existing_plans:
                    continue

                plan = Plan(
                    name=name,
                    display_name=display_name,
                    sort_order=sort_order,
                    description=description,
                    is_active=True,
                )
                db.add(plan)
                await db.flush()  # get plan.id

                for module_key, hard_limit in entitlements.items():
                    ent = PlanEntitlement(
                        plan_id=plan.id,
                        module_key=module_key,
                        hard_limit=hard_limit,
                    )
                    db.add(ent)

                new_count += 1

            if new_count > 0:
                await db.commit()
                logger.info(f"[seed_plans] Seeded {new_count} plan(s) with entitlements.")
            else:
                logger.info("[seed_plans] All default plans already seeded; no action taken.")
    except Exception as e:
        logger.error(f"[seed_plans] Failed to seed plans: {e}", exc_info=True)


async def seed_system_settings():
    """Ensure the single-row SystemSettings exists with defaults."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SystemSettings).where(SystemSettings.singleton_key == "global")
            )
            if not result.scalars().first():
                import copy
                from app.services.settings_service import SYSTEM_SETTINGS_DEFAULT
                ss = SystemSettings(
                    singleton_key="global",
                    settings_json=copy.deepcopy(SYSTEM_SETTINGS_DEFAULT),
                    version=1,
                )
                db.add(ss)
                await db.commit()
                logger.info("[seed_system_settings] Seeded default system settings.")
            else:
                logger.info("[seed_system_settings] System settings already exist.")
    except Exception as e:
        logger.error(f"[seed_system_settings] Failed: {e}", exc_info=True)
