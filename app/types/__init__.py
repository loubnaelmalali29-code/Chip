"""Core types for Chip's messaging system.

This package centralizes all enums, message models, adapter protocols, and
result/event schemas in one place to keep the codebase discoverable and
maintainable. Most modules should import types from here rather than directly
from submodules.

Usage:
    from app.types import TextMessage, MessagingAdapter, ServiceType
"""

from .enums import Effect, MessageType, ReactionType, ServiceType
from .events import NormalizedEvent
from .messages import (
    OutboundMessage,
    IMessageTextMessage,
    IMessageReactionMessage,
    IMessageAudioMessage,
)
from .protocols import MessagingAdapter
from .results import SendResult
from .api import MessagePayload, SendMessageRequest, SendMessageResponse

__all__ = [
    "ServiceType",
    "ReactionType",
    "MessageType",
    "OutboundMessage",
    "IMessageTextMessage",
    "IMessageReactionMessage",
    "IMessageAudioMessage",
    "SendResult",
    "NormalizedEvent",
    "MessagingAdapter",
    "Effect",
    "MessagePayload",
    "SendMessageRequest",
    "SendMessageResponse",
]
