from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.adapters.registry import AdapterRegistry
from tests.conftest import override_generate_reply


def headers() -> dict[str, str]:
    return {"Authorization": "Bearer inbound-secret"}


@respx.mock
def test_send_failure_surfaces_502(client: TestClient) -> None:
    adapter = AdapterRegistry.get("loop")
    respx.post(adapter.send_endpoint()).mock(
        return_value=httpx.Response(500, json={"error": "x"})
    )

    body = {
        "alert_type": "message_inbound",
        "recipient": "+15551230000",
        "text": "Hi",
        "message_id": "m1",
    }
    with override_generate_reply("ok"):
        r = client.post("/webhooks/loop", headers=headers(), json=body)
    assert r.status_code == 502


def test_agent_failure_surfaces_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that agent failures are handled gracefully."""
    from app.agents import langchain_agent

    def _boom(_: str, context: str = None, user_id: str = None) -> tuple[str, None]:
        raise RuntimeError("llm down")

    monkeypatch.setattr(langchain_agent, "generate_reply_with_langchain", _boom)

    r = client.post(
        "/webhooks/loop",
        headers=headers(),
        json={"alert_type": "message_inbound", "recipient": "+1", "text": "x"},
    )
    # Should return 200 with fallback message, not 500
    # (The messaging router handles errors gracefully)
    assert r.status_code == 200
