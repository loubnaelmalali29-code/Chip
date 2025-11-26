"""Simple in-memory conversation history for maintaining context."""

from __future__ import annotations

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

# Store conversation history per recipient
# Format: {recipient: [{"role": "user"|"assistant", "content": str, "timestamp": datetime}, ...]}
_conversation_history: Dict[str, List[Dict[str, any]]] = defaultdict(list)

# Clean up old conversations after 1 hour of inactivity
_CONVERSATION_TTL = timedelta(hours=1)
_last_activity: Dict[str, datetime] = {}


def _cleanup_old_conversations() -> None:
    """Remove conversations older than TTL."""
    now = datetime.now()
    expired_recipients = [
        recipient for recipient, last_time in _last_activity.items()
        if now - last_time > _CONVERSATION_TTL
    ]
    for recipient in expired_recipients:
        if recipient in _conversation_history:
            del _conversation_history[recipient]
        if recipient in _last_activity:
            del _last_activity[recipient]


def add_message(recipient: str, role: str, content: str) -> None:
    """Add a message to conversation history."""
    _cleanup_old_conversations()
    
    if recipient not in _conversation_history:
        _conversation_history[recipient] = []
    
    _conversation_history[recipient].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now()
    })
    
    # Keep only last 10 messages to avoid memory issues
    if len(_conversation_history[recipient]) > 10:
        _conversation_history[recipient] = _conversation_history[recipient][-10:]
    
    _last_activity[recipient] = datetime.now()


def get_conversation_history(recipient: str, max_messages: int = 5) -> List[Dict[str, str]]:
    """Get recent conversation history for a recipient."""
    _cleanup_old_conversations()
    
    if recipient not in _conversation_history:
        return []
    
    # Return last N messages
    messages = _conversation_history[recipient][-max_messages:]
    return [{"role": msg["role"], "content": msg["content"]} for msg in messages]


def clear_conversation(recipient: str) -> None:
    """Clear conversation history for a recipient."""
    if recipient in _conversation_history:
        del _conversation_history[recipient]
    if recipient in _last_activity:
        del _last_activity[recipient]



