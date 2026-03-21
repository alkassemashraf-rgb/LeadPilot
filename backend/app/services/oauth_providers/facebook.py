"""Facebook OAuth adapter. Standard OAuth 2.0. No refresh token — tokens are long-lived."""
import httpx
from .base import BaseOAuthAdapter


class FacebookOAuthAdapter(BaseOAuthAdapter):
    provider_code = "facebook"

    async def exchange_code(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                token_url,
                params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def normalize_account_metadata(self, token_response: dict) -> dict:
        return {
            "external_account_id": None,  # Resolved later via /me if needed
            "external_account_name": None,
            "expires_in": token_response.get("expires_in"),
            "token_type": token_response.get("token_type", "bearer"),
        }

    async def fetch_user_profile(self, access_token: str) -> dict:
        """Fetch user profile from Facebook Graph API."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.facebook.com/me",
                params={
                    "fields": "id,name,email,picture.type(large)",
                    "access_token": access_token,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        picture_url = None
        pic = data.get("picture", {})
        if isinstance(pic, dict):
            picture_url = pic.get("data", {}).get("url")

        return {
            "provider_user_id": data["id"],
            "email": data.get("email"),
            "full_name": data.get("name"),
            "avatar_url": picture_url,
        }
