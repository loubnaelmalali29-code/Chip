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
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage
    AIMessage = None  # Fallback if not available
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


SYSTEM_PROMPT = """You are Chip, a helpful AI assistant for the Alabama tech community. 

IMPORTANT GUIDELINES:
1. **Context Awareness**: When users say "option 1", "the second one", "number 2", etc., they're referring to items from your previous message. Always maintain context from the conversation.

2. **General Knowledge**: You have general knowledge. If asked about general topics (geography, history, science, etc.), answer helpfully. However, if the question is clearly unrelated to Alabama tech community, politely redirect: "I'm focused on helping the Alabama tech community, but I can answer that: [answer]. How can I help you with tech opportunities or challenges?"

3. **Database Context**: Only use database context when it's relevant to the user's question. If the user asks "what's the capital of France", don't search the database - just answer directly.

4. **Follow-up Questions**: When users select an option (like "I'm interested in option 2" or "tell me more about the second challenge"), understand they're referring to your previous list. Provide details about that specific item.

5. **Spelling**: Be understanding of typos and misspellings. If someone says "challege" or "intership", understand they mean "challenge" or "internship".

6. **Never Reset**: Never say "I'm here to help. What would you like to know?" in the middle of a conversation. Always maintain context and continue the conversation naturally.

Be warm, concise, and helpful. Use database context when relevant, but don't force it for unrelated questions."""


def generate_reply_with_langchain(
    user_message: str,
    context: Optional[str] = None,
    user_id: Optional[str] = None,
    recipient: Optional[str] = None,
    conversation_history: Optional[list] = None,
) -> tuple[str, Optional[Dict[str, Any]]]:
    """Generate reply using LangChain with Supabase RAG.
    
    Handles misspellings, maintains conversation context, and normalizes user input.
    """
    llm = _get_llm()
    
    # Clean and correct spelling in user message
    cleaned_message = extract_clean_message(user_message)
    corrected_message = correct_spelling(cleaned_message, aggressive=True)  # Use aggressive for better correction
    
    # Detect if this is a general knowledge question (not about database)
    is_general_question = _is_general_knowledge_question(corrected_message)
    
    # Only get database context if it's relevant (not a general knowledge question)
    search_query = corrected_message if corrected_message != cleaned_message else cleaned_message
    
    # Get context if not provided and it's not a general question
    if not context and not is_general_question:
        context = get_rag_service().get_context_for_query(search_query)
    elif is_general_question:
        context = ""  # Don't use database context for general questions
    
    # Build conversation context
    conversation_context = ""
    if conversation_history:
        conversation_context = "\n\nPrevious conversation:\n"
        for msg in conversation_history[-3:]:  # Last 3 messages
            role = "User" if msg.get("role") == "user" else "You"
            conversation_context += f"{role}: {msg.get('content', '')}\n"
    
    # Build prompt
    user_msg_for_prompt = corrected_message if corrected_message else cleaned_message
    
    # Detect if user is selecting an option
    is_option_selection = _is_selecting_option(user_msg_for_prompt)
    
    if is_option_selection and conversation_history:
        # User is selecting from previous list - emphasize context
        prompt = f"{conversation_context}\n\nUser is selecting an option from your previous message. Understand which item they're referring to and provide details about that specific item.\n\nUser: {user_msg_for_prompt}\n\nProvide detailed information about the selected item."
    elif context and context.strip() and "No specific context" not in context and not is_general_question:
        prompt = f"{conversation_context}\n\nDatabase context:\n{context}\n\nUser: {user_msg_for_prompt}\n\nGenerate a helpful response. Format opportunities/challenges nicely. Maintain conversation context."
    elif is_general_question:
        prompt = f"{conversation_context}\n\nUser: {user_msg_for_prompt}\n\nThis is a general knowledge question. Answer it helpfully, then gently redirect to Alabama tech community topics if appropriate."
    else:
        prompt = f"{conversation_context}\n\nUser: {user_msg_for_prompt}\n\nGenerate a helpful response about the Alabama tech community. Maintain conversation context."
    
    # Build messages with history
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    # Add conversation history
    if conversation_history:
        for msg in conversation_history[-3:]:  # Last 3 messages for context
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant" and AIMessage:
                try:
                    messages.append(AIMessage(content=msg.get("content", "")))
                except:
                    pass  # Fallback if AIMessage not available
    
    # Add current user message
    messages.append(HumanMessage(content=prompt))
    
    # Generate response
    try:
        reply = llm.invoke(messages).content.strip()
        if not reply or len(reply) < 10:
            reply = "I'm here to help! What would you like to know about the Alabama tech community?"
        # Remove the generic fallback if it appears in the middle of conversation
        if conversation_history and "I'm here to help" in reply and "What would you like to know" in reply:
            # Try to generate a more contextual response
            try:
                contextual_prompt = f"{conversation_context}\n\nUser: {user_msg_for_prompt}\n\nContinue the conversation naturally based on the context above."
                reply = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=contextual_prompt)]).content.strip()
            except:
                pass
    except Exception as e:
        print(f"LangChain error: {e}")
        reply = "I'm here to help! What would you like to know about the Alabama tech community?"
    
    # Use original message for submission detection to preserve user intent
    return reply, _detect_submission(user_message, context, user_id)


def _is_general_knowledge_question(text: str) -> bool:
    """Detect if this is a general knowledge question (not about database)."""
    text_lower = text.lower()
    
    # General knowledge indicators
    general_patterns = [
        r'what.*capital',
        r'what.*capital of',
        r'tell me.*joke',
        r'what.*weather',
        r'who.*president',
        r'what.*population',
        r'how.*many.*people',
        r'what.*date',
        r'what.*time',
    ]
    
    import re
    for pattern in general_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # If it doesn't contain tech community keywords, might be general
    tech_keywords = ['challenge', 'internship', 'opportunity', 'event', 'tech', 'alabama', 'community']
    if not any(keyword in text_lower for keyword in tech_keywords):
        # Check if it's a question about general topics
        question_words = ['what', 'who', 'when', 'where', 'why', 'how']
        if any(text_lower.startswith(qw) for qw in question_words):
            return True
    
    return False


def _is_selecting_option(text: str) -> bool:
    """Detect if user is selecting an option from a list."""
    text_lower = text.lower()
    
    option_patterns = [
        r'\b(option|choice|pick|select|choose|want|interested).*\b(1|2|3|4|5|first|second|third|fourth|fifth|one|two|three|four|five)\b',
        r'\b(the|that)\s+(1|2|3|4|5|first|second|third|fourth|fifth|one|two|three|four|five)\b',
        r'\b(1|2|3|4|5|first|second|third|fourth|fifth)\b.*(challenge|internship|opportunity|event)',
        r'\bnumber\s+(1|2|3|4|5)\b',
    ]
    
    import re
    for pattern in option_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False


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
        matches = re.findall(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            context,
            re.I,
        )
        if matches:
            return {
                "user_id": user_id,
                "challenge_id": matches[0],
                "submission_text": user_message,  # Keep original message
                "submission_url": None,
            }
    return None