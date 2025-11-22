from __future__ import annotations

from enum import Enum


class ServiceType(str, Enum):
    """Delivery channel preference for outbound messages.

    This indicates the desired transport when a provider supports more than
    one. For example, Loop can send via iMessage or SMS. Adapters may treat
    this as a hint and fall back based on device capabilities.

    - IMESSAGE: Prefer Apple iMessage if available
    - SMS: Use carrier SMS/MMS

    Example:
        >>> from app.types import TextMessage, ServiceType
        >>> TextMessage(recipient="+15551234567", text="Hi", service=ServiceType.IMESSAGE)
    """

    IMESSAGE = "imessage"
    SMS = "sms"


class ReactionType(str, Enum):
    """Set of reactions supported by Loop and normalized across adapters.

    These map to common tapback reactions. When sending, pair with
    `reply_to_id` to indicate which message is being reacted to.

    Example:
        >>> from app.types import ReactionMessage, ReactionType
        >>> ReactionMessage(recipient="+1", reaction=ReactionType.LIKE, reply_to_id="m1")
    """

    LOVE = "love"
    LIKE = "like"
    DISLIKE = "dislike"
    LAUGH = "laugh"
    EXCLAIM = "exclaim"
    QUESTION = "question"
    # Removal variants per Loop docs (prefix '-')
    LOVE_REMOVE = "-love"
    LIKE_REMOVE = "-like"
    DISLIKE_REMOVE = "-dislike"
    LAUGH_REMOVE = "-laugh"
    EXCLAIM_REMOVE = "-exclaim"
    QUESTION_REMOVE = "-question"
    UNKNOWN = "unknown"


class MessageType(str, Enum):
    """High-level classification for outbound and inbound messages.

    Adapters populate this when normalizing inbound events and message models
    set this for outbound types. Downstream systems can use it for routing
    or policy decisions.
    """

    TEXT = "text"
    REACTION = "reaction"
    AUDIO = "audio"
    ATTACHMENTS = "attachments"
    STICKER = "sticker"
    LOCATION = "location"


class Effect(str, Enum):
    """iMessage bubble/screen effects supported by Loop.

    Docs: `Loop Sending Messages`.
    """

    SLAM = "slam"
    LOUD = "loud"
    GENTLE = "gentle"
    INVISIBLE_INK = "invisibleInk"
    ECHO = "echo"
    SPOTLIGHT = "spotlight"
    BALLOONS = "balloons"
    CONFETTI = "confetti"
    LOVE = "love"
    LASERS = "lasers"
    FIREWORKS = "fireworks"
    SHOOTING_STAR = "shootingStar"
    CELEBRATION = "celebration"
