import time
import logging
from typing import Dict, Tuple, Optional, Any
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.db import get_db
from app.models.models import SystemModuleConfig

logger = logging.getLogger(__name__)

# --- Module Registry ---
MODULE_AUTH = "auth"
MODULE_EMAIL_ENGINE = "email_engine"
MODULE_EMAIL_VERIFICATION = "email_verification"
MODULE_PROMPT_STUDIO = "prompt_studio"
MODULE_KNOWLEDGE_FILES = "knowledge_files"
MODULE_INTEGRATIONS_HUB = "integrations_hub"
MODULE_INTEGRATIONS_CONNECT = "integrations_connect"
MODULE_WEBHOOKS_INGESTION = "webhooks_ingestion"
MODULE_RUNTIME_ENGINE = "runtime_engine"
MODULE_DISPATCH_ENGINE = "dispatch_engine"
MODULE_INBOX = "inbox"
MODULE_ZOHO_SYNC = "zoho_sync"
MODULE_ANALYTICS = "analytics"
MODULE_DIAGNOSTICS = "diagnostics"
MODULE_ADMIN_PORTAL = "admin_portal"

ALL_MODULES = [
    MODULE_AUTH, MODULE_EMAIL_ENGINE, MODULE_EMAIL_VERIFICATION,
    MODULE_PROMPT_STUDIO, MODULE_KNOWLEDGE_FILES, MODULE_INTEGRATIONS_HUB,
    MODULE_INTEGRATIONS_CONNECT, MODULE_WEBHOOKS_INGESTION, MODULE_RUNTIME_ENGINE,
    MODULE_DISPATCH_ENGINE, MODULE_INBOX, MODULE_ZOHO_SYNC, MODULE_ANALYTICS,
    MODULE_DIAGNOSTICS, MODULE_ADMIN_PORTAL
]

# --- Simple TTL Cache ---
class ModuleCache:
    def __init__(self, ttl_seconds: int = 15):
        self._cache: Dict[str, Tuple[float, bool]] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[bool]:
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: bool) -> None:
        self._cache[key] = (time.time(), value)

    def invalidate(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

module_cache = ModuleCache()

async def check_module_enabled(module_name: str, db: AsyncSession) -> bool:
    """Check if a module is enabled, utilizing a short-lived memory cache."""
    cached = module_cache.get(module_name)
    if cached is not None:
        return cached

    result = await db.execute(select(SystemModuleConfig).where(SystemModuleConfig.module_name == module_name))
    mod = result.scalars().first()
    
    # Modules are enabled by default if not seeded, EXCEPT for admin_portal which MUST be enabled
    is_enabled = mod.is_enabled if mod else True
    
    module_cache.set(module_name, is_enabled)
    return is_enabled

def require_module_enabled(module_name: str, action: str = "execute"):
    """
    Dependency factory to enforce module toggles on API endpoints.
    Throws 403 Forbidden if disabled.
    """
    async def _dependency(request: Request, db: AsyncSession = Depends(get_db)):
        is_enabled = await check_module_enabled(module_name, db)
        if not is_enabled:
            # The global exception handler will wrap this into a ResponseEnvelope
            raise HTTPException(
                status_code=403,
                detail=f"MODULE_DISABLED: Module '{module_name}' is currently disabled for action '{action}'."
            )
    return _dependency
