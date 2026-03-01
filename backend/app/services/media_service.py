"""Media download and storage service for WhatsApp inbound media."""
import logging
import os
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.whatsapp.adapter import WhatsAppAdapter
from app.models.models import Integration
from app.core.security import decrypt_data
from sqlmodel import select

logger = logging.getLogger(__name__)

STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")

MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/aac": "aac",
    "video/mp4": "mp4",
    "video/3gpp": "3gp",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


async def download_and_store_media(
    session: AsyncSession,
    workspace_id: UUID,
    media_id: str,
    mime_type: Optional[str],
    provider: str,
) -> Optional[str]:
    """Download media from WhatsApp and store locally. Returns relative path or None."""
    if provider != "whatsapp":
        return None

    # Resolve integration to get access token
    result = await session.execute(
        select(Integration).where(
            Integration.workspace_id == workspace_id,
            Integration.provider == "whatsapp",
        )
    )
    integration = result.scalars().first()
    if not integration or not integration.encrypted_config:
        logger.warning(f"No WhatsApp integration for workspace {workspace_id}")
        return None

    config = decrypt_data(integration.encrypted_config)
    adapter = WhatsAppAdapter(
        phone_number_id=integration.provider_workspace_id,
        access_token=config.get("access_token"),
    )

    # Get the download URL from WhatsApp
    media_url = await adapter.get_media_url(media_id)
    if not media_url:
        return None

    # Download the actual file
    data = await adapter.download_media(media_url)
    if not data:
        return None

    # Store to local filesystem
    ext = MIME_TO_EXT.get(mime_type, "bin")
    ws_dir = os.path.join(STORAGE_ROOT, str(workspace_id))
    os.makedirs(ws_dir, exist_ok=True)

    filename = f"{media_id}.{ext}"
    filepath = os.path.join(ws_dir, filename)

    with open(filepath, "wb") as f:
        f.write(data)

    relative_path = f"storage/{workspace_id}/{filename}"
    logger.info(f"Stored media {media_id} at {relative_path} ({len(data)} bytes)")
    return relative_path
