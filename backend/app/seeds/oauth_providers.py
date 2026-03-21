"""Idempotent seed script for OAuth provider registry.

Run directly:
    cd backend && python -m app.seeds.oauth_providers

Or called from the app lifespan startup hook.
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import OAuthProvider

logger = logging.getLogger(__name__)

_PROVIDERS = [
    {
        "provider_code": "facebook",
        "display_name": "Facebook",
        "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes_json": '["public_profile","email"]',
        "is_active": True,
        "supports_refresh_token": False,
    },
    {
        "provider_code": "tiktok",
        "display_name": "TikTok",
        "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes_json": '["user.info.basic"]',
        "is_active": True,
        "supports_refresh_token": True,
    },
    {
        "provider_code": "hubspot",
        "display_name": "HubSpot",
        "auth_url": "https://app.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        "scopes_json": '["crm.objects.contacts.read","crm.objects.deals.read"]',
        "is_active": True,
        "supports_refresh_token": True,
    },
    {
        "provider_code": "salesforce",
        "display_name": "Salesforce",
        "auth_url": "https://login.salesforce.com/services/oauth2/authorize",
        "token_url": "https://login.salesforce.com/services/oauth2/token",
        "scopes_json": '["api","refresh_token","offline_access"]',
        "is_active": True,
        "supports_refresh_token": True,
    },
]


async def seed_oauth_providers(db: AsyncSession) -> None:
    """Insert OAuth providers if they don't exist yet. Safe to call on every startup."""
    now = datetime.utcnow()
    inserted = 0
    skipped = 0

    for p in _PROVIDERS:
        result = await db.execute(
            select(OAuthProvider).where(OAuthProvider.provider_code == p["provider_code"])
        )
        existing = result.scalars().first()
        if existing:
            skipped += 1
            continue

        provider = OAuthProvider(
            **p,
            created_at=now,
            updated_at=now,
        )
        db.add(provider)
        inserted += 1

    if inserted:
        await db.commit()
        logger.info(f"OAuth providers seeded: {inserted} inserted, {skipped} already existed")
    else:
        logger.debug(f"OAuth provider seed: all {skipped} providers already present")


if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    # Load .env
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

    from app.core.db import get_db

    async def _run():
        async for session in get_db():
            await seed_oauth_providers(session)
            break

    asyncio.run(_run())
    print("Done.")
