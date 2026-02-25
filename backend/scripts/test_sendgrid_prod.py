import httpx
import asyncio
from app.core.config import settings

async def test_sendgrid():
    client = httpx.AsyncClient()
    headers = {
        'Authorization': f'Bearer {settings.SENDGRID_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'personalizations': [{'to': [{'email': 'alkassem.ashraf@gmail.com'}], 'subject': 'Diagnostic Integration Test'}],
        'from': {'email': settings.SENDGRID_FROM_EMAIL},
        'content': [{'type': 'text/plain', 'value': 'Verifying SendGrid API integration.'}]
    }
    
    print(f"API Key Starts With: {settings.SENDGRID_API_KEY[:7] if settings.SENDGRID_API_KEY else 'NONE'}")
    print(f"From Email: {settings.SENDGRID_FROM_EMAIL}")
    
    try:
        r = await client.post('https://api.sendgrid.com/v3/mail/send', headers=headers, json=payload)
        print('STATUS:', r.status_code)
        print('BODY:', r.text)
    except Exception as e:
        print('EXCEPTION:', repr(e))
    finally:
        await client.aclose()

if __name__ == '__main__':
    asyncio.run(test_sendgrid())
