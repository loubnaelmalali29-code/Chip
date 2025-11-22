from __future__ import annotations

from typing import Annotated, Union

from pydantic import BaseModel, Field

from .messages import IMessageAudioMessage, IMessageReactionMessage, IMessageTextMessage
from .results import SendResult


# Public discriminated union alias used by HTTP layer
MessagePayload = Annotated[
    Union[IMessageTextMessage, IMessageReactionMessage, IMessageAudioMessage],
    Field(discriminator="message_type"),
]


class SendMessageRequest(BaseModel):
    """Generic outbound send request model for API endpoints.

    Attributes:
        provider: Adapter to use (e.g., "loop"). Defaults to the primary provider.
        message: One of TextMessage, ReactionMessage, or AudioMessage. The
            `message_type` discriminator in JSON must be one of: "text",
            "reaction", or "audio".

    Examples:
        Text:
            {
              "provider": "loop",
              "message": {
                "message_type": "text",
                "recipient": "+15551230000",
                "text": "Hello",
                "service": "sms"
              }
            }

        Reaction:
            {
              "provider": "loop",
              "message": {
                "message_type": "reaction",
                "recipient": "+1",
                "reaction": "like",
                "reply_to_id": "m1"
              }
            }

        Audio:
            {
              "message": {
                "message_type": "audio",
                "recipient": "+1",
                "audio_url": "https://example.com/file.m4a",
                "text": "Hello"
              }
            }
    """

    provider: str = Field(default="loop")
    message: MessagePayload


class SendMessageResponse(BaseModel):
    """Standard response schema for outbound send API endpoints.

    Attributes:
        ok: Indicates request handling success.
        result: Adapter `SendResult` containing provider response details.
    """

    ok: bool
    result: SendResult
