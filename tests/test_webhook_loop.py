from __future__ import annotations

from typing import Any, Dict

import httpx
import respx
from fastapi.testclient import TestClient

from app.adapters.registry import AdapterRegistry
from tests.conftest import override_generate_reply


def loop_headers() -> Dict[str, str]:
    return {"Authorization": "Bearer inbound-secret"}


@respx.mock
def test_loop_webhook_message_inbound_triggers_send(client: TestClient) -> None:
    adapter = AdapterRegistry.get("loop")
    respx.post(adapter.send_endpoint()).mock(
        return_value=httpx.Response(200, json={"message_id": "out-1"})
    )

    payload: Dict[str, Any] = {
        "alert_type": "message_inbound",
        "recipient": "+15551230000",
        "text": "Hi Chip!",
        "message_type": "text",
        "message_id": "in-1",
        "api_version": "1.0",
    }

    with override_generate_reply("Hello there!"):
        r = client.post("/webhooks/loop", headers=loop_headers(), json=payload)

    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["received_text"] == "Hi Chip!"
    assert data["reply"] == "Hello there!"
    assert data["sent"]["message_id"] == "out-1"


def test_loop_webhook_auth_required(client: TestClient) -> None:
    r = client.post(
        "/webhooks/loop", json={"alert_type": "message_inbound", "text": "x"}
    )
    assert r.status_code == 401


@respx.mock
def test_loop_webhook_internal_shape_sends_when_recipient_present(
    client: TestClient,
) -> None:
    adapter = AdapterRegistry.get("loop")
    respx.post(adapter.send_endpoint()).mock(
        return_value=httpx.Response(200, json={"message_id": "out-2"})
    )

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
    with override_generate_reply("Echo!"):
        r = client.post("/webhooks/loop", headers=loop_headers(), json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "Echo!"
    assert data["sent"]["message_id"] == "out-2"


@respx.mock
def test_loop_webhook_internal_shape_no_recipient_does_not_send(
    client: TestClient,
) -> None:
    # do not register respx route to ensure no outbound call attempted

    body = {
        "event": "message.created",
        "data": {
            "conversationId": "conv_123",
            "message": {"id": "msg_abc", "text": "Hello"},
        },
    }
    with override_generate_reply("Echo!"):
        r = client.post("/webhooks/loop", headers=loop_headers(), json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["sent"] is None
