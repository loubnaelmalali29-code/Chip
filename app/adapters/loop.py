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
        """Normalize webhook payload to NormalizedEvent, handling various payload shapes and edge cases."""
        if not isinstance(body, dict):
            # Handle non-dict payloads gracefully
            return NormalizedEvent(
                alert_type=None,
                text=str(body) if body else "",
                recipient=None,
                message_id=None,
            )

        # Native Loop webhook shape
        if body.get("alert_type"):
            group = body.get("group")
            if isinstance(group, dict):
                group_id = group.get("group_id")
            elif isinstance(group, str):
                group_id = group
            else:
                group_id = None

            # Safely parse message_type
            message_type = None
            raw_message_type = body.get("message_type")
            if isinstance(raw_message_type, str):
                try:
                    # Try to match against known MessageType values
                    message_type_values = {m.value for m in MessageType}
                    if raw_message_type.lower() in {v.lower() for v in message_type_values}:
                        # Find the matching enum value (case-insensitive)
                        for mt in MessageType:
                            if mt.value.lower() == raw_message_type.lower():
                                message_type = mt
                                break
                except Exception:
                    pass

            # Safely parse reaction
            reaction = None
            raw_reaction = body.get("reaction")
            if isinstance(raw_reaction, str):
                try:
                    reaction_values = {r.value for r in ReactionType}
                    if raw_reaction.lower() in {v.lower() for v in reaction_values}:
                        for rt in ReactionType:
                            if rt.value.lower() == raw_reaction.lower():
                                reaction = rt
                                break
                except Exception:
                    pass

            # Extract text from various possible fields
            text = body.get("text", "")
            if not text:
                text = body.get("content", "")
            if not text:
                text = body.get("message", "")
            if not isinstance(text, str):
                text = str(text) if text else ""

            # Extract recipient from various possible fields
            recipient = body.get("recipient")
            if not recipient:
                recipient = body.get("from")
            if isinstance(recipient, dict):
                recipient = recipient.get("address") or recipient.get("recipient")
            if not isinstance(recipient, str):
                recipient = None

            # Extract message_id from various possible fields
            message_id = body.get("message_id")
            if not message_id:
                message_id = body.get("id")
            if not isinstance(message_id, str):
                message_id = None

            return NormalizedEvent(
                alert_type=body.get("alert_type"),
                text=text,
                recipient=recipient,
                message_id=message_id,
                group_id=group_id,
                message_type=message_type,
                reaction=reaction,
            )

        # Internal testing shape from plan
        data = body.get("data", {})
        if not isinstance(data, dict):
            data = {}

        message = data.get("message", {})
        if not isinstance(message, dict):
            message = {}

        # Extract text from nested message or data
        text = message.get("text", "")
        if not text:
            text = data.get("text", "")
        if not text:
            text = body.get("text", "")
        if not isinstance(text, str):
            text = str(text) if text else ""

        # Extract recipient
        recipient = None
        from_field = message.get("from")
        if isinstance(from_field, dict):
            recipient = from_field.get("address")
        elif isinstance(from_field, str):
            recipient = from_field
        if not recipient:
            recipient = data.get("from")
        if not recipient:
            recipient = body.get("from")
        if not isinstance(recipient, str):
            recipient = None

        # Extract message_id
        message_id = message.get("id")
        if not message_id:
            message_id = data.get("id")
        if not message_id:
            message_id = body.get("id")
        if not isinstance(message_id, str):
            message_id = None

        # Extract group_id
        group_id = data.get("conversationId")
        if not group_id:
            group_id = data.get("group_id")
        if not group_id:
            group_id = body.get("group_id")
        if not isinstance(group_id, str):
            group_id = None

        return NormalizedEvent(
            alert_type=body.get("event") or body.get("alert_type"),
            text=text,
            recipient=recipient,
            message_id=message_id,
            group_id=group_id,
        )
