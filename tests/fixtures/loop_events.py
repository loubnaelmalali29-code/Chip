from __future__ import annotations

from typing import Any, Dict, Optional


def inbound_text(
    *,
    recipient: str = "+15551230000",
    text: str = "Hello",
    message_id: str = "in-1",
    group_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "alert_type": "message_inbound",
        "recipient": recipient,
        "text": text,
        "message_type": "text",
        "message_id": message_id,
        "api_version": "1.0",
    }
    if group_id:
        payload["group"] = {"group_id": group_id}
    return payload


def internal_message_created(
    *,
    conversation_id: str = "conv_123",
    text: str = "Hello",
    from_address: str = "+15551239999",
    message_id: str = "msg_abc",
) -> Dict[str, Any]:
    return {
        "event": "message.created",
        "data": {
            "conversationId": conversation_id,
            "message": {
                "id": message_id,
                "text": text,
                "from": {"channel": "sms", "address": from_address},
            },
        },
    }

