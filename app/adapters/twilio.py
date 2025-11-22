from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from app.types import (
    MessagingAdapter,
    SendResult,
    NormalizedEvent,
    OutboundMessage,
    IMessageTextMessage,
)


class TwilioClient(MessagingAdapter):
    """Twilio adapter implementing the MessagingAdapter protocol.

    Notes:
    - Webhook verification: Optional. If TWILIO_WEBHOOK_SECRET is not set, verification is skipped.
      If set, compares provided token to TWILIO_WEBHOOK_SECRET for basic verification.
      (Full X-Twilio-Signature HMAC validation can be added when request URL/body are available).
    - send_message: Fully implemented using Twilio Messages API.
    """

    def __init__(self) -> None:
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER", "")
        # Optional: If not set, webhook verification is skipped
        self.webhook_secret = os.getenv("TWILIO_WEBHOOK_SECRET")

    # --- Outbound ---
    def send_message(self, message: OutboundMessage) -> SendResult:  # type: ignore[override]
        """Send a message via Twilio using the Messages API.
        
        Uses Twilio's REST API: POST /Accounts/{AccountSid}/Messages.json
        Requires: To, From, Body parameters
        Authentication: Basic Auth with AccountSid:AuthToken
        """
        if not self.account_sid or not self.auth_token:
            raise RuntimeError(
                "Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN environment variables"
            )
        if not self.from_number:
            raise RuntimeError("Missing TWILIO_FROM_NUMBER environment variable")

        # Only text messages are supported for SMS
        if not isinstance(message, IMessageTextMessage):
            raise ValueError("Twilio SMS only supports text messages")

        # Validate message has a target
        message.ensure_valid_target()

        # Twilio requires recipient (To), not group_id for SMS
        if not message.recipient:
            raise ValueError("Twilio SMS requires a recipient phone number")

        # Construct Twilio API URL
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Messages.json"
        )

        # Prepare form data (Twilio expects form-encoded, not JSON)
        data = {
            "To": message.recipient,
            "From": self.from_number,
            "Body": message.text,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                # Use Basic Auth: AccountSid:AuthToken
                response = client.post(
                    url,
                    data=data,  # form-encoded data
                    auth=(self.account_sid, self.auth_token),
                )
                response.raise_for_status()
                
                # Parse Twilio response
                twilio_data = response.json()
                # Twilio returns "sid" as the message ID
                message_id = twilio_data.get("sid")
                status = twilio_data.get("status", "")
                
                # Status will be "queued" for successful sends
                ok = status in ("queued", "sending", "sent")
                
                return SendResult(
                    message_id=message_id,
                    ok=ok,
                    data=twilio_data if isinstance(twilio_data, dict) else None,
                )
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors (4xx, 5xx)
            error_data = None
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            return SendResult(
                message_id=None,
                ok=False,
                data={
                    "error": f"HTTP {e.response.status_code}",
                    "detail": error_data or e.response.text,
                },
            )
        except httpx.RequestError as e:
            # Handle network errors
            return SendResult(
                message_id=None,
                ok=False,
                data={"error": "Network error", "detail": str(e)},
            )
        except Exception as e:
            # Handle unexpected errors
            return SendResult(
                message_id=None,
                ok=False,
                data={"error": "Unexpected error", "detail": str(e)},
            )

    # --- Webhook verification ---
    def verify_request(self, authorization_header: Optional[str]) -> None:
        """Verify webhook request authenticity.
        
        If TWILIO_WEBHOOK_SECRET is not set, verification is skipped (allows all requests).
        This is fine for development/testing. For production, set TWILIO_WEBHOOK_SECRET
        or implement proper X-Twilio-Signature HMAC validation.
        """
        # Skip verification if webhook secret is not configured
        if not self.webhook_secret:
            return  # No verification - allows all requests (OK for development)
        
        provided = authorization_header or ""
        # Support raw secret or Bearer <secret>
        if provided.startswith("Bearer "):
            provided = provided[len("Bearer ") :]
        if provided != self.webhook_secret:
            raise PermissionError("Unauthorized webhook")

    # --- Normalization ---
    def normalize_event(self, body: Dict[str, Any]) -> NormalizedEvent:
        """Normalize a Twilio inbound message webhook to our internal shape.

        Twilio webhook fields for Messaging (SMS/WhatsApp) typically include:
        - From, To, Body, MessageSid, etc. (form-encoded by default)
        We support JSON-shaped testing bodies as well.
        """
        if not isinstance(body, dict):
            body = {}
        text = body.get("Body") or body.get("text") or ""
        recipient = body.get("From") or (body.get("from", {}) or {}).get("address")
        message_id = body.get("MessageSid") or body.get("message_id")
        return NormalizedEvent(
            alert_type=body.get("SmsStatus") or body.get("event"),
            text=text,
            recipient=recipient,
            message_id=message_id,
            group_id=None,
        )
