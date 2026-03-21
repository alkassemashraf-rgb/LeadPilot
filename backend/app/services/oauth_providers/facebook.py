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
