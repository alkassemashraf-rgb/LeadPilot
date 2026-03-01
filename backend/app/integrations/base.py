"""Abstract base class for messaging adapters."""
from abc import ABC, abstractmethod
from typing import Optional


class MessagingAdapter(ABC):
    @abstractmethod
    async def send_text(self, to: str, text: str) -> str:
        """Send a text message. Returns provider_message_id."""
        ...

    @abstractmethod
    async def send_media(
        self, to: str, media_type: str, media_url: str, caption: Optional[str] = None
    ) -> str:
        """Send a media message. Returns provider_message_id."""
        ...
