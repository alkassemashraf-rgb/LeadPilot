"""HubSpot OAuth adapter. Standard OAuth 2.0 with refresh tokens."""
import httpx
from .base import BaseOAuthAdapter


class HubSpotOAuthAdapter(BaseOAuthAdapter):
    provider_code = "hubspot"

    async def exchange_code(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()

    async def refresh_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()

    def normalize_account_metadata(self, token_response: dict) -> dict:
        return {
            "external_account_id": str(token_response.get("hub_id", "")),
            "external_account_name": token_response.get("hub_domain"),
            "expires_in": token_response.get("expires_in"),
            "token_type": token_response.get("token_type", "bearer"),
        }
