from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Body, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.registry import AdapterRegistry
from app.types import (
    NormalizedEvent,
    SendMessageRequest,
    SendMessageResponse,
    IMessageTextMessage,
    MessageType,
)
from app.agents.langchain_agent import generate_reply_with_langchain
from app.services.supabase_rag import get_rag_service
from app.services.user_service import get_user_service
from app.services.submission_service import get_submission_service
from app.utils.spelling import extract_clean_message


router = APIRouter(prefix="", tags=["messaging"])
security = HTTPBearer(auto_error=False)

# Initialize services (singletons)
_rag_service = get_rag_service()
_user_service = get_user_service()
_submission_service = get_submission_service()

# Message deduplication: track processed messages to prevent duplicate processing
# Using a simple in-memory cache with TTL (cleans up after 1 hour)
# Key format: "message_id|recipient|text_hash" for better deduplication
_processed_messages: dict[str, datetime] = {}
_MESSAGE_CACHE_TTL = timedelta(hours=1)
_RATE_LIMIT_WINDOW = timedelta(seconds=10)  # Don't process same user messages within 10 seconds


def _cleanup_old_messages() -> None:
    """Remove messages older than TTL from the cache."""
    now = datetime.now()
    expired = [key for key, timestamp in _processed_messages.items() if now - timestamp > _MESSAGE_CACHE_TTL]
    for key in expired:
        del _processed_messages[key]


def _get_message_key(message_id: str | None, recipient: str | None, text: str) -> str:
    """Generate a unique key for message deduplication."""
    import hashlib
    text_hash = hashlib.md5(text.strip().lower().encode()).hexdigest()[:8]
    return f"{message_id or 'no-id'}|{recipient or 'no-recipient'}|{text_hash}"


def _is_message_processed(message_id: str | None, recipient: str | None, text: str) -> bool:
    """Check if a message has already been processed recently."""
    _cleanup_old_messages()
    key = _get_message_key(message_id, recipient, text)
    
    if key in _processed_messages:
        # Check if it's within rate limit window
        last_processed = _processed_messages[key]
        if datetime.now() - last_processed < _RATE_LIMIT_WINDOW:
            return True
    
    return False


def _mark_message_processed(message_id: str | None, recipient: str | None, text: str) -> None:
    """Mark a message as processed."""
    key = _get_message_key(message_id, recipient, text)
    _processed_messages[key] = datetime.now()


@router.post("/messages/send")
async def send_message(payload: SendMessageRequest) -> SendMessageResponse:
    adapter = AdapterRegistry.get(payload.provider)
    try:
        payload.message.ensure_valid_target()
        result = adapter.send_message(payload.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Send error: {e}")
    return SendMessageResponse(ok=True, result=result)


@router.post("/webhooks/{provider}")
async def webhook_events(
    provider: str,
    payload: dict[str, Any] = Body(..., description="Raw webhook JSON payload"),
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> dict[str, Any]:
    """Generic webhook handler for any provider.

    - Verifies the request using the adapter's `verify_request`
    - Normalizes inbound payload to `NormalizedEvent`
    - Calls the agent to generate replies
    - If a recipient is present, sends a text reply via the same adapter
    """
    print(f"WEBHOOK RECEIVED - Provider: {provider}")
    
    adapter = AdapterRegistry.get(provider)

    try:
        token = credentials.credentials if credentials is not None else None
        adapter.verify_request(token)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Unauthorized webhook")

    # Normalize the event - handles various payload shapes and message types
    try:
        normalized: NormalizedEvent = adapter.normalize_event(
            payload if isinstance(payload, dict) else {}
        )
    except Exception as e:
        print(f"Error normalizing event: {e}")
        return {"ok": True, "error": f"Failed to normalize event: {str(e)}"}

    alert_type = normalized.alert_type
    message_id = normalized.message_id
    recipient = normalized.recipient
    message_type = normalized.message_type
    text = normalized.text or ""
    
    # Handle different message types
    # Only process text messages and messages without a specific type (assumed to be text)
    if message_type and message_type not in (MessageType.TEXT, None):
        # For non-text messages (audio, reactions, etc.), send a helpful response
        if message_type == MessageType.AUDIO:
            if recipient:
                try:
                    adapter.send_message(
                        IMessageTextMessage(
                            recipient=recipient,
                            text="I received your audio message! Could you send that as text? I'm better at understanding written messages.",
                        )
                    )
                except Exception as e:
                    if "280" not in str(e) and "opted out" not in str(e).lower():
                        print(f"Error sending audio response: {e}")
            return {"ok": True, "ignored": True, "reason": "Audio message - requested text"}
        elif message_type == MessageType.REACTION:
            # Reactions don't need responses
            return {"ok": True, "ignored": True, "reason": "Reaction message - no response needed"}
        else:
            # Other message types - try to extract text or send helpful message
            if not text and recipient:
                try:
                    adapter.send_message(
                        IMessageTextMessage(
                            recipient=recipient,
                            text="I received your message, but I'm best at handling text messages. Could you send that as text?",
                        )
                    )
                except Exception as e:
                    if "280" not in str(e) and "opted out" not in str(e).lower():
                        print(f"Error sending message type response: {e}")
            return {"ok": True, "ignored": True, "reason": f"Non-text message type: {message_type}"}
    
    if alert_type and alert_type != "message_inbound":
        print(f"Ignoring non-message event: alert_type={alert_type}")
        return {"ok": True, "ignored": True, "reason": f"Not a user message (alert_type: {alert_type})"}

    import os
    bot_sender = os.environ.get("LOOP_SENDER_NAME", "chip@ai.imsg.bot")
    if recipient and recipient.lower() == bot_sender.lower():
        print(f"Ignoring message from bot itself: recipient={recipient}")
        return {"ok": True, "ignored": True, "reason": "Message from bot itself"}

    # Clean and extract text message
    cleaned_text = extract_clean_message(text)
    
    is_duplicate = _is_message_processed(message_id, recipient, cleaned_text)
    if is_duplicate:
        return {"ok": True, "ignored": True, "reason": "Message already processed recently"}

    user_id = None
    if recipient:
        try:
            user_id = _user_service.get_or_create_user(phone_number=recipient)
        except Exception as e:
            print(f"Error getting/creating user: {e}")
            # Continue processing even if user creation fails

    if recipient and cleaned_text and cleaned_text.strip():
        try:
            # Use cleaned text for context search
            context = _rag_service.get_context_for_query(cleaned_text)
            reply_text, submission_data = generate_reply_with_langchain(
                user_message=cleaned_text,  # Use cleaned text for processing
                context=context,
                user_id=str(user_id) if user_id else None,
            )
            
            if submission_data and user_id:
                try:
                    from uuid import UUID
                    submission = _submission_service.create_submission(
                        user_id=UUID(str(user_id)),
                        challenge_id=UUID(submission_data["challenge_id"]),
                        submission_text=submission_data["submission_text"],
                        submission_url=submission_data.get("submission_url"),
                    )
                    if submission and "submission" not in reply_text.lower():
                        reply_text = f"Thanks! I've recorded your submission.\n\n{reply_text}"
                except Exception as e:
                    print(f"Error creating submission: {e}")
            
            _mark_message_processed(message_id, recipient, cleaned_text)
            
            try:
                adapter.send_message(
                    IMessageTextMessage(
                        recipient=recipient,
                        text=reply_text,
                    )
                )
            except Exception as send_error:
                error_str = str(send_error)
                if "280" not in error_str and "opted out" not in error_str.lower():
                    print(f"Error sending message: {send_error}")
        except Exception as e:
            _mark_message_processed(message_id, recipient, cleaned_text)
            import traceback
            print(f"ERROR: LangChain response generation failed: {e}")
            print(traceback.format_exc())
            
            # Try to send a helpful error message to the user
            if recipient:
                try:
                    adapter.send_message(
                        IMessageTextMessage(
                            recipient=recipient,
                            text="I'm having trouble processing that right now. Could you try rephrasing your message?",
                        )
                    )
                except Exception as send_error:
                    if "280" not in str(send_error) and "opted out" not in str(send_error).lower():
                        print(f"Error sending error message: {send_error}")
            
            return {"ok": True, "error": "Failed to generate reply", "message_processed": True}
    elif recipient:
        # Empty or whitespace-only message
        _mark_message_processed(message_id, recipient, cleaned_text if cleaned_text else "")
        try:
            adapter.send_message(
                IMessageTextMessage(
                    recipient=recipient,
                    text="Thanks for your message! I'm Chip, your Alabama tech community AI agent. How can I help you today?",
                )
            )
        except Exception as e:
            if "280" not in str(e) and "opted out" not in str(e).lower():
                print(f"Error sending acknowledgment: {e}")

    return {
        "ok": True,
    }
