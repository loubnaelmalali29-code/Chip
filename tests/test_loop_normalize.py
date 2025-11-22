from __future__ import annotations

from app.adapters.registry import AdapterRegistry


def test_normalize_native_inbound() -> None:
    body = {
        "alert_type": "message_inbound",
        "recipient": "+15551230000",
        "text": "Hi",
        "message_id": "m1",
        "group": {"group_id": "g1"},
    }
    adapter = AdapterRegistry.get("loop")
    norm = adapter.normalize_event(body)
    assert norm.text == "Hi"
    assert norm.recipient == "+15551230000"
    assert norm.message_id == "m1"
    assert norm.group_id == "g1"


def test_normalize_internal_shape() -> None:
    body = {
        "event": "message.created",
        "data": {
            "conversationId": "conv_123",
            "message": {
                "id": "msg_abc",
                "text": "Hello",
                "from": {"channel": "sms", "address": "+15551239999"},
            },
        },
    }
    adapter = AdapterRegistry.get("loop")
    norm = adapter.normalize_event(body)
    assert norm.text == "Hello"
    assert norm.recipient == "+15551239999"
    assert norm.message_id == "msg_abc"
    assert norm.group_id == "conv_123"
