import logging
from typing import Optional
from pathlib import Path
from email.message import EmailMessage
import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings

logger = logging.getLogger(__name__)

# Setup Jinja2 environment
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "email"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)

class EmailService:
    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        message_id: Optional[str] = None,
        email_log_id: Optional[str] = None,
    ) -> bool:
        """
        Send an email using the configured provider.
        """
        if settings.EMAIL_PROVIDER == "console":
            print(f"\n[EMAIL DEBUG] To: {to_email}")
            print(f"[EMAIL DEBUG] Subject: {subject}")
            print(f"[EMAIL DEBUG] Body: \n{text_content or html_content}")
            print("-" * 20 + "\n")
            return True

        if settings.EMAIL_PROVIDER == "sendgrid":
            from app.services.email_providers.sendgrid_provider import SendGridProvider, EmailTransportError
            provider = SendGridProvider()
            try:
                return await provider.send_email(
                    to_email=to_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    message_id=message_id,
                    email_log_id=email_log_id
                )
            except EmailTransportError as e:
                logger.error(f"SendGrid provider failed: {e}")
                raise

        if settings.EMAIL_PROVIDER == "smtp":
            return await EmailService._send_via_smtp(to_email, subject, html_content, text_content, message_id)

        logger.warning(f"Unknown EMAIL_PROVIDER: {settings.EMAIL_PROVIDER} or provider not fully implemented.")
        return False

    @staticmethod
    async def _send_via_smtp(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
        message_id: Optional[str] = None,
    ) -> bool:
        message = EmailMessage()
        if message_id:
            message["Message-ID"] = message_id
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        message["To"] = to_email
        message["Subject"] = subject

        if text_content and html_content:
            message.set_content(text_content)
            message.add_alternative(html_content, subtype='html')
        elif html_content:
            message.set_content(html_content, subtype='html')
        elif text_content:
            message.set_content(text_content)

        client = aiosmtplib.SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_USE_SSL,
        )
        
        try:
            if not settings.SMTP_USE_SSL:
                await client.connect(use_tls=False)
                if settings.SMTP_USE_TLS:
                    await client.starttls()
            else:
                await client.connect()
            
            await client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            await client.send_message(message)
            return True
        finally:
            if client.is_connected:
                await client.quit()

    @staticmethod
    async def send_password_reset_email(to_email: str, token: str, message_id: Optional[str] = None, email_log_id: Optional[str] = None) -> bool:
        base_url = settings.APP_BASE_URL or settings.FRONTEND_URL
        base_url = base_url.rstrip("/")
        reset_link = f"{base_url}/reset-password?token={token}"
        subject = f"Reset your password for {settings.PROJECT_NAME}"
        
        context = {
            "project_name": settings.PROJECT_NAME,
            "reset_link": reset_link
        }
        
        html_template = jinja_env.get_template("password_reset.html")
        txt_template = jinja_env.get_template("password_reset.txt")
        
        html_content = html_template.render(**context)
        text_content = txt_template.render(**context)
        
        return await EmailService.send_email(to_email, subject, html_content, text_content, message_id, email_log_id)

    @staticmethod
    async def send_invite_email(to_email: str, token: str, workspace_name: str, inviter_name: str, message_id: Optional[str] = None, email_log_id: Optional[str] = None) -> bool:
        base_url = settings.APP_BASE_URL or settings.FRONTEND_URL
        base_url = base_url.rstrip("/")
        invite_link = f"{base_url}/accept-invite?token={token}"
        
        subject = f"You've been invited to join {workspace_name} on {settings.PROJECT_NAME}"
        
        context = {
            "project_name": settings.PROJECT_NAME,
            "inviter_name": inviter_name,
            "workspace_name": workspace_name,
            "invite_link": invite_link
        }
        
        html_template = jinja_env.get_template("workspace_invite.html")
        txt_template = jinja_env.get_template("workspace_invite.txt")
        
        html_content = html_template.render(**context)
        text_content = txt_template.render(**context)
        
        return await EmailService.send_email(to_email, subject, html_content, text_content, message_id, email_log_id)

    @staticmethod
    async def send_verification_email(to_email: str, token: str, message_id: Optional[str] = None, email_log_id: Optional[str] = None) -> bool:
        from datetime import datetime
        base_url = settings.APP_BASE_URL or settings.FRONTEND_URL
        base_url = base_url.rstrip("/")
        verification_link = f"{base_url}/verify-email?token={token}"
        
        subject = f"Verify your email for {settings.PROJECT_NAME}"
        
        context = {
            "project_name": settings.PROJECT_NAME,
            "verification_link": verification_link,
            "year": datetime.utcnow().year,
        }
        
        html_template = jinja_env.get_template("verify_email.html")
        txt_template = jinja_env.get_template("verify_email.txt")
        
        html_content = html_template.render(**context)
        text_content = txt_template.render(**context)
        
        return await EmailService.send_email(to_email, subject, html_content, text_content, message_id, email_log_id)
