"""Meta Graph API service — centralized helpers for OAuth, webhook subscription, Lead Ads."""
import httpx
import logging

from app.services.metrics_service import metrics

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v18.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


async def subscribe_page_webhooks(page_id: str, page_access_token: str) -> bool:
    """Subscribe a page to webhook fields for messaging + lead ads."""
    url = f"{GRAPH_BASE_URL}/{page_id}/subscribed_apps"
    params = {"access_token": page_access_token}
    data = {"subscribed_fields": "messages,messaging_postbacks,feed,leadgen"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, params=params, data=data)
            if response.status_code == 200 and response.json().get("success"):
                metrics.increment("meta_webhook_subscribed")
                logger.info(f"Subscribed page {page_id} to webhooks")
                return True
            logger.error(f"Webhook subscription failed for {page_id}: {response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Network error subscribing webhooks for {page_id}: {e}")
            return False


async def verify_page_subscription(page_id: str, page_access_token: str) -> dict:
    """Check current webhook subscriptions for a page."""
    url = f"{GRAPH_BASE_URL}/{page_id}/subscribed_apps"
    params = {"access_token": page_access_token}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            return {"error": response.text}
        except httpx.RequestError as e:
            return {"error": str(e)}


async def fetch_lead_data(leadgen_id: str, page_access_token: str) -> dict:
    """Fetch lead submission data from Meta Graph API."""
    url = f"{GRAPH_BASE_URL}/{leadgen_id}"
    params = {"access_token": page_access_token}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            error_msg = response.text
            logger.error(f"Failed to fetch lead {leadgen_id}: {error_msg}")
            metrics.increment("meta_leads_failed")
            raise Exception(f"Failed to fetch lead data: {error_msg}")
        except httpx.RequestError as e:
            logger.error(f"Network error fetching lead {leadgen_id}: {e}")
            metrics.increment("meta_leads_failed")
            raise Exception(f"Network error fetching lead: {e}")


def parse_lead_fields(field_data: list) -> dict:
    """Normalize Meta lead field_data array into a flat dict."""
    result = {}
    field_map = {
        "email": "email",
        "phone_number": "phone",
        "full_name": "full_name",
        "first_name": "first_name",
        "last_name": "last_name",
    }

    for field in field_data:
        name = field.get("name", "").lower()
        values = field.get("values", [])
        if name in field_map and values:
            result[field_map[name]] = values[0]

    # Split full_name into first/last if separate fields missing
    if "full_name" in result and "first_name" not in result:
        parts = result["full_name"].split(" ", 1)
        result["first_name"] = parts[0]
        result["last_name"] = parts[1] if len(parts) > 1 else ""

    return result


async def get_user_profile(user_id: str, page_access_token: str) -> dict:
    """Fetch user profile from Meta Graph API. Non-critical — returns {} on failure."""
    url = f"{GRAPH_BASE_URL}/{user_id}"
    params = {
        "fields": "first_name,last_name,profile_pic",
        "access_token": page_access_token,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            logger.warning(f"Failed to fetch profile for {user_id}: {response.status_code}")
            return {}
        except httpx.RequestError as e:
            logger.warning(f"Network error fetching profile for {user_id}: {e}")
            return {}
