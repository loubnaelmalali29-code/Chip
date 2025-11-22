import os
from typing import Any, Dict, Optional

import httpx

from app.types import (
    MessagingAdapter,
    SendResult,
    NormalizedEvent,
    ReactionType,
    MessageType,
    OutboundMessage,
    IMessageTextMessage,
    IMessageReactionMessage,
    IMessageAudioMessage,
)


class LoopClient(MessagingAdapter):
    """LoopMessage adapter implementing the MessagingAdapter protocol.

    Sends text messages to an individual recipient (phone/email) or a group.
    Also provides webhook verification and normalization helpers.
    """

    def __init__(self) -> None:
        # Default to production endpoint. Sandbox testing uses same endpoint with sandbox recipients
        # If sandbox endpoint is needed, it may be: https://server.loopmessage.com/api/v1/message/send/
        # (same as production - sandbox is determined by recipient being in sandbox list)
        self.send_url = os.getenv(
            "LOOP_SEND_URL", "https://server.loopmessage.com/api/v1/message/send/"
        )
        self.authorization = os.environ.get("LOOP_AUTHORIZATION", "")
        self.secret_key = os.environ.get("LOOP_SECRET_KEY", "")
        self.sender_name = os.environ.get("LOOP_SENDER_NAME", "")
        self.status_callback = os.environ.get("STATUS_CALLBACK_URL")
        self.status_callback_auth = os.environ.get("STATUS_CALLBACK_AUTH")
        self.webhook_auth = os.environ.get("LOOP_WEBHOOK_AUTH")

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Authorization": self.authorization,
            "Loop-Secret-Key": self.secret_key,
            "Content-Type": "application/json",
        }
        return headers

    # Compatibility helper for tests using endpoint discovery
    def send_endpoint(self) -> str:  # type: ignore[override]
        return self.send_url

    def _build_payload(self, message: OutboundMessage) -> Dict[str, Any]:
        """
        Helper to unpack OutboundMessage into the payload for the LoopMessage REST API call.

        See: https://docs.loopmessage.com/imessage-conversation-api/send-message#send-single-message
        """
        payload: Dict[str, Any] = {}

        # Only include sender_name if it's set (required for production, optional for sandbox)
        if self.sender_name:
            payload["sender_name"] = self.sender_name

        if getattr(message, "group_id", None):
            payload["group"] = message.group_id
        elif getattr(message, "recipient", None):
            payload["recipient"] = message.recipient

        if self.status_callback:
            payload["status_callback"] = self.status_callback
        if self.status_callback_auth:
            payload["status_callback_header"] = self.status_callback_auth
        if getattr(message, "reply_to_id", None):
            payload["reply_to_id"] = message.reply_to_id
        if getattr(message, "passthrough", None):
            payload["passthrough"] = message.passthrough
        if getattr(message, "service", None):
            payload["service"] = message.service.value
        if getattr(message, "timeout_seconds", None) and message.timeout_seconds >= 5:
            payload["timeout"] = message.timeout_seconds

        if isinstance(message, IMessageTextMessage):
            payload["text"] = message.text
            if getattr(message, "attachments", None):
                payload["attachments"] = message.attachments
            if getattr(message, "subject", None):
                payload["subject"] = message.subject
            if getattr(message, "effect", None):
                payload["effect"] = message.effect.value
        elif isinstance(message, IMessageReactionMessage):
            payload["reaction"] = message.reaction.value
            payload["message_id"] = message.target_message_id
            if "reply_to_id" in payload:
                del payload["reply_to_id"]
        elif isinstance(message, IMessageAudioMessage):
            payload["media_url"] = message.media_url
            if getattr(message, "text", None):
                payload["text"] = message.text

        return payload

    def send_message(self, message: OutboundMessage) -> SendResult:  # type: ignore[override]
        """Send a message via Loop using the extensible message object."""
        if not self.authorization or not self.secret_key:
            raise RuntimeError(
                "Missing LOOP_AUTHORIZATION or LOOP_SECRET_KEY environment variables"
            )

        message.ensure_valid_target()
        payload = self._build_payload(message)

        with httpx.Client(timeout=15) as client:
            response = client.post(self.send_url, headers=self._headers(), json=payload)
            try:
                response.raise_for_status()
                data = response.json()
                message_id = data.get("message_id") if isinstance(data, dict) else None
                ok = data.get("ok") if isinstance(data, dict) else None
                return SendResult(
                    message_id=message_id,
                    ok=ok,
                    data=data if isinstance(data, dict) else None,
                )
            except httpx.HTTPStatusError as e:
                try:
                    error_detail = e.response.json()
                except Exception:
                    error_detail = e.response.text
                print(f"Loop API Error: {error_detail}")
                raise

    # Webhook helpers
    def verify_request(self, authorization_header: Optional[str]) -> None:
        if not self.webhook_auth:
            return
        expected = self.webhook_auth
        provided = authorization_header or ""
        if provided.startswith("Bearer "):
            provided = provided[len("Bearer ") :]
        if provided != expected:
            raise PermissionError("Unauthorized webhook")

    def normalize_event(self, body: Dict[str, Any]) -> NormalizedEvent:
        # Native Loop webhook shape
        if isinstance(body, dict) and body.get("alert_type"):
            group = body.get("group") if isinstance(body.get("group"), dict) else None
            message_type = body.get("message_type")
            reaction = body.get("reaction")
            return NormalizedEvent(
                alert_type=body.get("alert_type"),
                text=body.get("text", ""),
                recipient=body.get("recipient"),
                message_id=body.get("message_id"),
                group_id=group.get("group_id") if isinstance(group, dict) else None,
                message_type=MessageType(message_type)
                if isinstance(message_type, str)
                and message_type in {m.value for m in MessageType}
                else None,
                reaction=ReactionType(reaction)
                if isinstance(reaction, str)
                and reaction in {r.value for r in ReactionType}
                else None,
            )

        # Internal testing shape from plan
        data = body.get("data", {}) if isinstance(body, dict) else {}
        message = data.get("message", {}) if isinstance(data, dict) else {}
        return NormalizedEvent(
            alert_type=body.get("event"),
            text=message.get("text", ""),
            recipient=message.get("from", {}).get("address")
            if isinstance(message.get("from"), dict)
            else None,
            message_id=message.get("id"),
            group_id=data.get("conversationId") if isinstance(data, dict) else None,
        )
