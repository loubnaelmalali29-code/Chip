"""LangChain response generator - simple and short."""

import os
import re
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from langchain_groq import ChatGroq
except ImportError:
    from langchain_community.chat_models import ChatGroq
try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage
from app.services.supabase_rag import get_rag_service
from app.utils.spelling import correct_spelling, extract_clean_message


def _get_llm():
    """Get LLM - tries Gemini, Groq, then OpenAI."""
    if key := os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"), google_api_key=key, temperature=0.7)
    if key := os.getenv("GROQ_API_KEY"):
        return ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"), groq_api_key=key, temperature=0.7)
    if key := os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), openai_api_key=key, temperature=0.7)
    raise RuntimeError("No LLM API key found. Set GOOGLE_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY")


SYSTEM_PROMPT = "You are Chip, a helpful AI assistant for the Alabama tech community. Help users find opportunities, challenges, and connect with the community. Be warm, concise, and use database context when available."


def generate_reply_with_langchain(
    user_message: str,
    context: Optional[str] = None,
    user_id: Optional[str] = None,
) -> tuple[str, Optional[Dict[str, Any]]]:
    """Generate reply using LangChain with Supabase RAG.
    
    Handles misspellings and normalizes user input before processing.
    """
    llm = _get_llm()
    
    # Clean and correct spelling in user message
    cleaned_message = extract_clean_message(user_message)
    corrected_message = correct_spelling(cleaned_message, aggressive=False)
    
    # Use corrected message for context search if original was significantly different
    search_query = corrected_message if corrected_message != cleaned_message else cleaned_message
    
    # Get context if not provided
    if not context:
        context = get_rag_service().get_context_for_query(search_query)
    
    # Build prompt with both original and corrected message for context
    user_msg_for_prompt = corrected_message if corrected_message else cleaned_message
    
    if context and context.strip() and "No specific context" not in context:
        prompt = f"Use this database context:\n{context}\n\nUser: {user_msg_for_prompt}\n\nGenerate a helpful response. Format opportunities/challenges nicely. Be understanding of any typos or misspellings in the user's message."
    else:
        prompt = f"User: {user_msg_for_prompt}\n\nGenerate a helpful response about the Alabama tech community. Be understanding of any typos or misspellings in the user's message."
    
    # Generate response
    try:
        reply = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]).content.strip()
        if not reply or len(reply) < 10:
            reply = "I'm here to help! What would you like to know about the Alabama tech community?"
    except Exception as e:
        print(f"LangChain error: {e}")
        reply = "I'm here to help! What would you like to know about the Alabama tech community?"
    
    # Use original message for submission detection to preserve user intent
    return reply, _detect_submission(user_message, context, user_id)


def _detect_submission(user_message: str, context: Optional[str], user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Detect if message is a challenge submission.
    
    Handles misspellings in submission-related keywords.
    """
    if not user_id:
        return None
    
    # Normalize message for keyword detection (handles misspellings)
    normalized_msg = user_message.lower()
    corrected_msg = correct_spelling(normalized_msg, aggressive=False)
    
    # Check for submission keywords (including common misspellings)
    submission_keywords = [
        "submitted", "submission", "completed", "finished", "done",
        "submited", "submition", "compleated", "compleate"
    ]
    
    if not any(kw in corrected_msg or kw in normalized_msg for kw in submission_keywords):
        return None
    
    if context and "challenge" in context.lower():
        matches = re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', context, re.I)
        if matches:
            return {
                "user_id": user_id,
                "challenge_id": matches[0],
                "submission_text": user_message,  # Keep original message
                "submission_url": None
            }
    return None

