import httpx
import logging
from typing import Optional

from app.integrations.base import MessagingAdapter

logger = logging.getLogger(__name__)


class WhatsAppAdapter(MessagingAdapter):
    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        self._headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _classify_error(self, response: httpx.Response, data: dict) -> Exception:
        """Classify API errors for retry logic."""
        error = data.get("error", {})
        error_code = error.get("code")
        error_subcode = error.get("error_subcode")
        error_message = error.get("message", "Unknown error")

        logger.error(f"WhatsApp API error: {error_message} (Code: {error_code}, Subcode: {error_subcode})")

        if response.status_code in [400, 401, 403]:
            return Exception(f"PERMANENT_FAILURE: {error_message} (Code: {error_code})")
        if response.status_code in [429, 500, 502, 503, 504]:
            return Exception(f"TRANSIENT_FAILURE: {error_message} (Code: {error_code})")
        return Exception(f"UNCLASSIFIED_FAILURE: {error_message} (Status: {response.status_code})")

    async def send_text(self, to: str, text: str) -> str:
        """Send a text message. Returns provider_message_id."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, headers=self._headers, json=payload)
                data = response.json()

                if response.status_code == 200:
                    provider_message_id = data.get("messages", [{}])[0].get("id")
                    logger.info(f"WhatsApp message sent successfully: {provider_message_id}")
                    return provider_message_id

                raise self._classify_error(response, data)

            except httpx.RequestError as e:
                logger.error(f"WhatsApp Network error: {str(e)}")
                raise Exception(f"TRANSIENT_FAILURE: Network error: {str(e)}")

    async def send_media(
        self, to: str, media_type: str, media_url: str, caption: Optional[str] = None
    ) -> str:
        """Send a media message (image, video, document, audio). Returns provider_message_id."""
        media_obj = {"link": media_url}
        if caption and media_type in ("image", "video", "document"):
            media_obj["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: media_obj,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, headers=self._headers, json=payload)
                data = response.json()

                if response.status_code == 200:
                    provider_message_id = data.get("messages", [{}])[0].get("id")
                    logger.info(f"WhatsApp media ({media_type}) sent: {provider_message_id}")
                    return provider_message_id

                raise self._classify_error(response, data)

            except httpx.RequestError as e:
                logger.error(f"WhatsApp Network error: {str(e)}")
                raise Exception(f"TRANSIENT_FAILURE: Network error: {str(e)}")

    async def get_media_url(self, media_id: str) -> Optional[str]:
        """Get the download URL for a media object. Returns URL string or None."""
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self._headers)
                if response.status_code == 200:
                    return response.json().get("url")
                logger.error(f"Failed to get media URL for {media_id}: {response.status_code}")
                return None
            except httpx.RequestError as e:
                logger.error(f"Network error getting media URL: {e}")
                return None

    async def download_media(self, media_url: str) -> Optional[bytes]:
        """Download media binary from a WhatsApp media URL."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    media_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if response.status_code == 200:
                    return response.content
                logger.error(f"Failed to download media: {response.status_code}")
                return None
            except httpx.RequestError as e:
                logger.error(f"Network error downloading media: {e}")
                return None

    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a received message as read."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, headers=self._headers, json=payload)
                return response.status_code == 200
            except httpx.RequestError as e:
                logger.error(f"Failed to mark message as read: {e}")
                return False
