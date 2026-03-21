"""Base OAuth adapter interface. All provider adapters must implement this."""
from abc import ABC, abstractmethod

from urllib.parse import urlencode


class BaseOAuthAdapter(ABC):
    """Provider-specific OAuth logic isolated here. Routes/services never contain provider conditionals."""

    provider_code: str

    def build_authorize_url(
        self,
        auth_url: str,
        scopes: list[str],
        client_id: str,
        redirect_uri: str,
        state: str,
    ) -> str:
        """Build the full authorization URL to redirect the user to. Default: standard OAuth2 params."""
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_type": "code",
        }
        params.update(self._extra_authorize_params())
        return f"{auth_url}?{urlencode(params)}"

    def _extra_authorize_params(self) -> dict:
        """Provider-specific extra params for the authorization URL. Override as needed."""
        return {}

    @abstractmethod
    async def exchange_code(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> dict:
        """Exchange an authorization code for access/refresh tokens. Returns raw provider response."""
        ...

    async def refresh_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict:
        """Refresh an access token. Returns raw provider response. Raises NotImplementedError if unsupported."""
        raise NotImplementedError(f"{self.provider_code} does not support token refresh")

    def normalize_account_metadata(self, token_response: dict) -> dict:
        """Extract external_account_id and external_account_name from token response. Override per provider."""
        return {
            "external_account_id": token_response.get("user_id") or token_response.get("id"),
            "external_account_name": token_response.get("name") or token_response.get("display_name"),
            "expires_in": token_response.get("expires_in"),
            "token_type": token_response.get("token_type", "bearer"),
        }

    async def fetch_user_profile(self, access_token: str) -> dict:
        """Fetch and normalize user profile from the provider using the access token.

        Returns a dict with keys:
            provider_user_id (str): unique user ID from the provider
            email (str | None): user email, or None if unavailable
            full_name (str | None): display name
            avatar_url (str | None): profile picture URL

        Override per provider. Raises NotImplementedError if not supported.
        """
        raise NotImplementedError(f"{self.provider_code} does not implement fetch_user_profile")
