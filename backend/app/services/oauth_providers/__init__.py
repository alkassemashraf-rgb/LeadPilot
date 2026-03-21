"""OAuth provider adapter registry. Add new providers here."""
from .base import BaseOAuthAdapter
from .facebook import FacebookOAuthAdapter
from .tiktok import TikTokOAuthAdapter
from .hubspot import HubSpotOAuthAdapter
from .salesforce import SalesforceOAuthAdapter

_REGISTRY: dict[str, BaseOAuthAdapter] = {
    "facebook": FacebookOAuthAdapter(),
    "tiktok": TikTokOAuthAdapter(),
    "hubspot": HubSpotOAuthAdapter(),
    "salesforce": SalesforceOAuthAdapter(),
}


def get_adapter(provider_code: str) -> BaseOAuthAdapter:
    adapter = _REGISTRY.get(provider_code)
    if not adapter:
        raise KeyError(f"No OAuth adapter registered for provider: {provider_code}")
    return adapter


__all__ = ["BaseOAuthAdapter", "get_adapter"]
