from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from .events import NormalizedEvent
from .messages import OutboundMessage
from .results import SendResult


class MessagingAdapter(Protocol):
    """Protocol for messaging providers.

    Concrete implementations encapsulate provider-specific HTTP and webhook
    normalization so routers remain provider-agnostic.

    Responsibilities:
        - Convert `OutboundMessage` to provider payloads and send
        - Verify incoming webhook authenticity
        - Normalize provider webhook bodies to `NormalizedEvent`

    Minimal example:
        >>> from typing import Dict
        >>> import httpx
        >>> from app.types import MessagingAdapter, OutboundMessage, SendResult
        >>> class ExampleAdapter(MessagingAdapter):
        ...     def __init__(self) -> None:
        ...         self.url = "https://example.com/send"
        ...     def send_endpoint(self) -> str:  # type: ignore[override]
        ...         return self.url
        ...     def send_message(self, message: OutboundMessage) -> SendResult:
        ...         with httpx.Client(timeout=10) as client:
        ...             r = client.post(self.url, json={"text": getattr(message, "text", "")})
        ...             r.raise_for_status()
        ...             data: Dict[str, Any] = r.json()
        ...         return SendResult(message_id=data.get("message_id"), data=data)
        ...     def verify_request(self, authorization_header: Optional[str]) -> None:
        ...         return None
        ...     def normalize_event(self, body: Dict[str, Any]) -> NormalizedEvent:
        ...         return NormalizedEvent(text=str(body.get("text", "")))
    """

    def send_endpoint(self) -> str:
        """Return the full URL endpoint used for sending messages for this adapter."""
        ...

    def send_message(self, message: OutboundMessage) -> SendResult:
        """Send an outbound message.

        Implementations should raise provider-specific errors or HTTP errors on
        failure; routers map these into appropriate API responses.
        """
        ...

    def verify_request(self, authorization_header: Optional[str]) -> None:
        """Raise if the incoming webhook request is not authorized."""
        ...

    def normalize_event(self, body: Dict[str, Any]) -> NormalizedEvent:
        """Normalize an inbound webhook payload to a common shape."""
        ...
