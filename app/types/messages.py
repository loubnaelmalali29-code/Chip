from __future__ import annotations

from typing import Optional, Literal

from pydantic import BaseModel
from pydantic import field_validator, model_validator

from .enums import Effect, MessageType, ReactionType, ServiceType


class OutboundMessage(BaseModel):
    """Base class for all outbound messages shared across providers.

    This model centralizes addressing, threading, and cross-cutting options so
    we avoid ever-growing keyword argument lists. Extend this class to add new
    message types that carry specific payload fields while inheriting common
    behaviors.

    Anatomy:
    - recipient or group_id: one is required to target a person or a group
    - reply_to_id: associates the message with a previous message/thread
    - passthrough: opaque correlation ID echoed in webhooks
    - service: desired delivery channel (e.g., iMessage, SMS)
    - timeout_seconds: per-message sending timeout (provider-specific)

    Example:
        >>> from app.types import IMessageTextMessage
        >>> msg = IMessageTextMessage(recipient="+1555", text="Hello")
        >>> msg.ensure_valid_target()
    """

    # Per Loop docs, recipient is required for single-recipient sends
    recipient: Optional[str] = None
    group_id: Optional[str] = None
    reply_to_id: Optional[str] = None
    passthrough: Optional[str] = None
    service: Optional[ServiceType] = None
    timeout_seconds: Optional[int] = None

    message_type: MessageType

    def ensure_valid_target(self) -> None:
        """Validate that either `recipient` or `group_id` is present.

        For Loop API, single send requires `recipient`; group send requires
        `group_id`. Routers may set the correct one based on context.
        """
        if not self.recipient and not self.group_id:
            raise ValueError("Either recipient or group_id must be provided")


class IMessageTextMessage(OutboundMessage):
    """iMessage text message (Loop Conversation API).

    This class intentionally encodes iMessage-specific capabilities and limits
    documented by Loop (effects, subject, attachments behavior). Providers like
    Twilio SMS should use a separate `SmsTextMessage` instead of reusing this.

    Fields:
        text: content to send (required by Loop)
        subject: optional bold title before the text (iMessage only)
        attachments: up to three https image URLs (PNG/JPG/JPEG/GIF/WEBP)
        effect: optional iMessage effect per docs

    Examples:
        >>> from app.types import IMessageTextMessage, Effect
        >>> IMessageTextMessage(recipient="+1", text="Hi", effect=Effect.CONFETTI)
        >>> IMessageTextMessage(group_id="g", text="Welcome", subject="Hello Team")
    """

    text: str
    subject: Optional[str] = None
    attachments: Optional[list[str]] = None
    effect: Optional[Effect] = None
    message_type: Literal["text"] = "text"

    @field_validator("attachments")
    @classmethod
    def _validate_attachments(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate attachments list according to Loop spec.

        - Max 3 URLs
        - Each URL must be https and length <= 256
        - Attachments represent images; we conservatively require common image extensions
        """
        if v is None:
            return v
        if len(v) > 3:
            raise ValueError("attachments cannot have more than 3 URLs")
        validated: list[str] = []
        for url in v:
            if not isinstance(url, str):
                raise ValueError("attachment URL must be a string")
            if len(url) > 256:
                raise ValueError("attachment URL exceeds 256 characters")
            if not url.startswith("https://"):
                raise ValueError("attachment URL must use https scheme")
            lower = url.lower()
            if not any(
                lower.endswith(ext)
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]
            ):
                raise ValueError(
                    "attachments must be image URLs (png/jpg/jpeg/gif/webp)"
                )
            validated.append(url)
        return validated

    @model_validator(mode="after")
    def _enforce_service_constraints(self) -> "IMessageTextMessage":
        """Enforce SMS limitations and general rules from Loop docs.

        - SMS does not support subject, effect, or reply_to_id
        - attachments in SMS only pictures (already enforced above)
        """
        if self.service == ServiceType.SMS:
            if self.subject is not None:
                raise ValueError("SMS does not support 'subject'")
            if self.effect is not None:
                raise ValueError("SMS does not support 'effect'")
            if self.reply_to_id is not None:
                raise ValueError("SMS does not support 'reply_to_id'")
        return self


class IMessageReactionMessage(OutboundMessage):
    """iMessage tapback reaction to an existing message.

    Fields:
        reaction: type of reaction to apply (includes '-' removal variants)
        target_message_id: required message_id to react to

    Example:
        >>> from app.types import IMessageReactionMessage, ReactionType
        >>> IMessageReactionMessage(recipient="+1", reaction=ReactionType.LIKE, target_message_id="m1")
    """

    reaction: ReactionType
    target_message_id: str
    message_type: Literal["reaction"] = "reaction"

    @model_validator(mode="after")
    def _enforce_reaction_constraints(self) -> "IMessageReactionMessage":
        """Enforce reaction rules.

        - Reactions are iMessage-only; reject SMS requests
        - Cannot combine with effect (not applicable here, but guarded at adapter)
        """
        if self.service == ServiceType.SMS:
            raise ValueError("SMS does not support reactions")
        return self


class IMessageAudioMessage(OutboundMessage):
    """iMessage audio message with optional accompanying text.

    Fields:
        media_url: HTTPS URL of the audio file
        text: optional text to send with the audio

    Example:
        >>> from app.types import IMessageAudioMessage
        >>> IMessageAudioMessage(recipient="+1", media_url="https://example.com/file.m4a", text="Hello")
    """

    media_url: str
    text: Optional[str] = None
    message_type: Literal["audio"] = "audio"

    @field_validator("media_url")
    @classmethod
    def _validate_media_url(cls, v: str) -> str:
        if not isinstance(v, str) or not v:
            raise ValueError("media_url is required")
        if not v.startswith("https://"):
            raise ValueError("media_url must use https scheme")
        return v

    @model_validator(mode="after")
    def _enforce_audio_constraints(self) -> "IMessageAudioMessage":
        """Enforce audio rules.

        - SMS cannot send audio messages
        """
        if self.service == ServiceType.SMS:
            raise ValueError("SMS does not support audio messages")
        return self
