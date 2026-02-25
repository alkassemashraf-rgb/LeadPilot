"""
Startup seed utilities: Ensures all canonical modules have a row in SystemModuleConfig.
Runs once on app startup; idempotent (uses INSERT or IGNORE logic via get-or-create).
"""
import logging
from app.core.db import SessionLocal as AsyncSessionLocal
from app.models.models import SystemModuleConfig
from app.core.modules import ALL_MODULES, MODULE_ADMIN_PORTAL
from sqlmodel import select

logger = logging.getLogger(__name__)


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
