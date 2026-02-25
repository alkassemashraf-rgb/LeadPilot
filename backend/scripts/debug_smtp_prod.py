import asyncio
import sys
import logging
from app.core.config import settings
import aiosmtplib
from email.message import EmailMessage

async def main():
    print("--- SMTP SETTINGS ---")
    print(f"Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    print(f"SSL: {settings.SMTP_USE_SSL}")
    print(f"TLS: {settings.SMTP_USE_TLS}")
    print(f"User: {settings.SMTP_USERNAME}")
    print(f"From: {settings.EMAIL_FROM}")
    print("---------------------\n")

    msg = EmailMessage()
    msg['Subject'] = 'LeadPilot Direct Diagnostic Test'
    msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg['To'] = 'alkassem.ashraf@gmail.com'
    msg.set_content('This is a raw SMTP diagnostic test to verify network delivery from the HF space directly to Hostinger.')

    # Using sys.stdout for logs
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    client = aiosmtplib.SMTP(
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        use_tls=settings.SMTP_USE_SSL,
    )
    
    try:
        print("Connecting...")
        if not settings.SMTP_USE_SSL:
            await client.connect(use_tls=False)
            if settings.SMTP_USE_TLS:
                print("Starting TLS...")
                await client.starttls()
        else:
            await client.connect()
            
        print("Logging in...")
        auth_resp = await client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        print(f"Auth Response: {auth_resp}")
        
        print("Sending message...")
        send_resp = await client.send_message(msg)
        print(f"\n======== SEND RESPONSE ========\n{send_resp}\n===============================")
        
    except Exception as e:
        print(f"SMTP Error: {repr(e)}")
    finally:
        await client.quit()

if __name__ == '__main__':
    asyncio.run(main())
