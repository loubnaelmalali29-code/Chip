from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .enums import MessageType, ReactionType


class NormalizedEvent(BaseModel):
    """Adapter-agnostic normalized inbound event.

    Routers should depend on this model rather than provider-specific webhook
    shapes. Adapters are responsible for mapping their payloads to this common
    schema. Fields are optional where providers may omit data.

    Attributes:
        alert_type: Provider-specific event name (e.g., "message_inbound").
        text: Plain text content, if present.
        recipient: Address or identifier of the intended recipient (if known).
        message_id: Unique identifier of the inbound message.
        group_id: Identifier for group conversation context when available.
        reaction: Parsed reaction type for reaction events.
        message_type: High-level type of the inbound message.

    Example:
        >>> from app.types import NormalizedEvent
        >>> NormalizedEvent(text="Hi", recipient="+1", message_id="m1")
    """

    alert_type: Optional[str] = None
    text: str = ""
    recipient: Optional[str] = None
    message_id: Optional[str] = None
    group_id: Optional[str] = None
    reaction: Optional[ReactionType] = None
    message_type: Optional[MessageType] = None
