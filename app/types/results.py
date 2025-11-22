from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class SendResult(BaseModel):
    """Standardized result returned by adapters after attempting to send.

    Attributes:
        message_id: Provider-assigned identifier for the outbound message.
        ok: Convenience flag when providers return `{ "ok": true }` style results.
        data: Raw provider response payload for debugging or advanced consumers.

    Example:
        >>> from app.types import SendResult
        >>> SendResult(message_id="m1", ok=True)
    """

    message_id: Optional[str] = None
    ok: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None
