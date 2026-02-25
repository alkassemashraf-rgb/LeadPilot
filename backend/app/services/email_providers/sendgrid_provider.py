import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailTransportError(Exception):
    pass

class SendGridProvider:
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        message_id: Optional[str] = None,
        email_log_id: Optional[str] = None
    ) -> bool:
        if not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL:
            raise EmailTransportError("SendGrid is not fully configured.")
            
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        content = []
        if text_content:
            content.append({"type": "text/plain", "value": text_content})
        if html_content:
            content.append({"type": "text/html", "value": html_content})
            
        payload = {
            "personalizations": [{
                "to": [{"email": to_email}],
                "subject": subject,
                "custom_args": {}
            }],
            "from": {
                "email": settings.SENDGRID_FROM_EMAIL,
                "name": settings.SENDGRID_FROM_NAME or settings.EMAIL_FROM_NAME or "LeadPilot"
            },
            "reply_to": {
                "email": settings.SENDGRID_FROM_EMAIL
            },
            "content": content
        }
        
        if message_id:
            payload["personalizations"][0]["custom_args"]["idempotency_key"] = str(message_id)
        if email_log_id:
            payload["personalizations"][0]["custom_args"]["email_log_id"] = str(email_log_id)
            
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as e:
                raise EmailTransportError(f"SendGrid HTTP request failed: {e}")
                
            if response.status_code == 202:
                return True
                
            error_msg = f"SendGrid API Error {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise EmailTransportError(error_msg)
