"""TikTok OAuth adapter. Uses client_key/client_secret naming and POST for token exchange."""
import httpx
from urllib.parse import urlencode
from .base import BaseOAuthAdapter


class TikTokOAuthAdapter(BaseOAuthAdapter):
    provider_code = "tiktok"

    def build_authorize_url(
        self,
        auth_url: str,
        scopes: list[str],
        client_id: str,
        redirect_uri: str,
        state: str,
    ) -> str:
        # TikTok uses client_key instead of client_id
        params = {
            "client_key": client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(scopes),
            "state": state,
            "response_type": "code",
        }
        return f"{auth_url}?{urlencode(params)}"

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
                    "client_key": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            # TikTok wraps response in data.data
            return data.get("data", data)

    async def refresh_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict:
        refresh_url = token_url.replace("/token/", "/refresh_token/")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                refresh_url,
                data={
                    "client_key": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", data)

    def normalize_account_metadata(self, token_response: dict) -> dict:
        return {
            "external_account_id": token_response.get("open_id"),
            "external_account_name": None,
            "expires_in": token_response.get("expires_in"),
            "token_type": "bearer",
        }
