import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class MetaAdapter:
    def __init__(self, page_id: str, page_access_token: str):
        self.page_id = page_id
        self.page_access_token = page_access_token
        self.base_url = "https://graph.facebook.com/v18.0/me/messages"

    async def send_text(self, recipient_id: str, text: str) -> str:
        """
        Send a text message via Meta Graph API (Messenger/Instagram).
        Returns the provider_message_id on success.
        """
        headers = {
            "Content-Type": "application/json",
        }
        params = {
            "access_token": self.page_access_token
        }
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
            "messaging_type": "RESPONSE"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, headers=headers, params=params, json=payload)
                data = response.json()

                if response.status_code == 200:
                    provider_message_id = data.get("message_id")
                    logger.info(f"Meta message sent successfully: {provider_message_id}")
                    return provider_message_id
                
                # Error classification
                error = data.get("error", {})
                error_code = error.get("code")
                error_message = error.get("message", "Unknown error")
                
                logger.error(f"Meta API error: {error_message} (Code: {error_code})")

                # Permanent failures
                if response.status_code in [400, 401, 403]:
                    raise Exception(f"PERMANENT_FAILURE: {error_message} (Code: {error_code})")
                
                # Transient failures
                if response.status_code in [429, 500, 502, 503, 504]:
                    raise Exception(f"TRANSIENT_FAILURE: {error_message} (Code: {error_code})")
                
                raise Exception(f"UNCLASSIFIED_FAILURE: {error_message} (Status: {response.status_code})")

            except httpx.RequestError as e:
                logger.error(f"Meta Network error: {str(e)}")
                raise Exception(f"TRANSIENT_FAILURE: Network error: {str(e)}")
