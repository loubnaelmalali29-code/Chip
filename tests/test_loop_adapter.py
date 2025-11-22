from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.adapters.registry import AdapterRegistry
from app.types import (
    IMessageTextMessage,
    IMessageReactionMessage,
    IMessageAudioMessage,
    ReactionType,
    ServiceType,
    Effect,
)


@respx.mock
def test_send_text_individual_success() -> None:
    adapter = AdapterRegistry.get("loop")

    route = respx.post(adapter.send_endpoint()).mock(
        return_value=httpx.Response(200, json={"message_id": "m1", "ok": True})
    )

    resp = adapter.send_message(
        IMessageTextMessage(recipient="+15551234567", text="Hello!")
    )

    assert route.called
    sent = json.loads(route.calls.last.request.content.decode())
    assert sent["text"] == "Hello!"
    assert sent["recipient"] == "+15551234567"
    assert sent["sender_name"]
    assert resp.message_id == "m1"


@respx.mock
def test_send_text_group_with_reply_and_timeout() -> None:
    adapter = AdapterRegistry.get("loop")

    route = respx.post(adapter.send_endpoint()).mock(
        return_value=httpx.Response(200, json={"message_id": "g1"})
    )

    resp = adapter.send_message(
        IMessageTextMessage(
            group_id="group-123",
            text="Welcome",
            reply_to_id="prior-1",
            passthrough="trace=abc",
            service=ServiceType.IMESSAGE,
            timeout_seconds=10,
            subject="Greetings",
            attachments=["https://example.com/pic.png"],
            effect=Effect.CONFETTI,
        )
    )

    assert route.called
    payload = json.loads(route.calls.last.request.content.decode())
    assert payload["group"] == "group-123"
    assert payload["reply_to_id"] == "prior-1"
    assert payload["passthrough"] == "trace=abc"
    assert payload["service"] == "imessage"
    assert payload["timeout"] == 10
    assert payload["subject"] == "Greetings"
    assert payload["attachments"] == ["https://example.com/pic.png"]
    assert payload["effect"] == "confetti"
    assert resp.message_id == "g1"


def test_send_text_requires_sender_and_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOOP_AUTHORIZATION", raising=False)
    adapter = AdapterRegistry.get("loop")
    with pytest.raises(RuntimeError):
        adapter.send_message(IMessageTextMessage(recipient="x", text="y"))


@respx.mock
def test_send_reaction_with_reply() -> None:
    adapter = AdapterRegistry.get("loop")
    route = respx.post(adapter.send_endpoint()).mock(
        return_value=httpx.Response(200, json={"message_id": "r1"})
    )

    resp = adapter.send_message(
        IMessageReactionMessage(
            recipient="+15550000000",
            reaction=ReactionType.LIKE,
            target_message_id="prior-xyz",
        )
    )

    assert route.called
    payload = json.loads(route.calls.last.request.content.decode())
    assert payload["recipient"] == "+15550000000"
    assert payload["reaction"] == "like"
    assert payload["message_id"] == "prior-xyz"
    assert resp.message_id == "r1"


def test_reaction_disallows_sms() -> None:
    adapter = AdapterRegistry.get("loop")
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageReactionMessage(
                recipient="+1",
                reaction=ReactionType.LIKE,
                target_message_id="m1",
                service=ServiceType.SMS,
            )
        )


def test_text_sms_disallows_subject_effect_reply_to() -> None:
    adapter = AdapterRegistry.get("loop")
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageTextMessage(
                recipient="+1",
                text="hi",
                service=ServiceType.SMS,
                subject="x",
            )
        )
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageTextMessage(
                recipient="+1",
                text="hi",
                service=ServiceType.SMS,
                effect=Effect.CONFETTI,
            )
        )
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageTextMessage(
                recipient="+1",
                text="hi",
                service=ServiceType.SMS,
                reply_to_id="m1",
            )
        )


def test_attachments_validation() -> None:
    adapter = AdapterRegistry.get("loop")
    # too many
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageTextMessage(
                recipient="+1",
                text="x",
                attachments=["a.png", "b.png", "c.png", "d.png"],
            )
        )
    # not https
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageTextMessage(
                recipient="+1", text="x", attachments=["http://example.com/p.png"]
            )
        )
    # not image extension
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageTextMessage(
                recipient="+1", text="x", attachments=["https://example.com/file.txt"]
            )
        )


def test_audio_sms_disallowed_and_https_required() -> None:
    adapter = AdapterRegistry.get("loop")
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageAudioMessage(
                recipient="+1",
                media_url="https://ok.com/a.m4a",
                service=ServiceType.SMS,
            )
        )
    with pytest.raises(ValueError):
        adapter.send_message(
            IMessageAudioMessage(recipient="+1", media_url="http://bad.com/a.m4a")
        )


@respx.mock
def test_send_audio_with_optional_text() -> None:
    adapter = AdapterRegistry.get("loop")
    route = respx.post(adapter.send_endpoint()).mock(
        return_value=httpx.Response(200, json={"message_id": "a1"})
    )

    resp = adapter.send_message(
        IMessageAudioMessage(
            recipient="+15551112222",
            media_url="https://example.com/file.m4a",
            text="Hello",
        )
    )

    assert route.called
    payload = json.loads(route.calls.last.request.content.decode())
    assert payload["recipient"] == "+15551112222"
    assert payload["media_url"] == "https://example.com/file.m4a"
    assert payload["text"] == "Hello"
    assert resp.message_id == "a1"


def test_message_requires_target() -> None:
    adapter = AdapterRegistry.get("loop")
    with pytest.raises(ValueError):
        adapter.send_message(IMessageTextMessage(text="no target"))
