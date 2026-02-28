import httpx
import logging

logger = logging.getLogger(__name__)

class WhatsAppAdapter:
    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"

    async def send_text(self, to: str, text: str) -> str:
        """
        Send a text message via WhatsApp Cloud API.
        Returns the provider_message_id on success.
        Raises an exception on failure with classification for retry logic.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=payload)
                data = response.json()

                if response.status_code == 200:
                    provider_message_id = data.get("messages", [{}])[0].get("id")
                    logger.info(f"WhatsApp message sent successfully: {provider_message_id}")
                    return provider_message_id
                
                # Error classification
                error = data.get("error", {})
                error_code = error.get("code")
                error_subcode = error.get("error_subcode")
                error_message = error.get("message", "Unknown error")
                
                logger.error(f"WhatsApp API error: {error_message} (Code: {error_code}, Subcode: {error_subcode})")

                # Permanent failures
                if response.status_code in [400, 401, 403]:
                    raise Exception(f"PERMANENT_FAILURE: {error_message} (Code: {error_code})")
                
                # Transient failures (Retryable)
                if response.status_code in [429, 500, 502, 503, 504]:
                    raise Exception(f"TRANSIENT_FAILURE: {error_message} (Code: {error_code})")
                
                raise Exception(f"UNCLASSIFIED_FAILURE: {error_message} (Status: {response.status_code})")

            except httpx.RequestError as e:
                logger.error(f"WhatsApp Network error: {str(e)}")
                raise Exception(f"TRANSIENT_FAILURE: Network error: {str(e)}")
