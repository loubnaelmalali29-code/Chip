"""LangChain response generator - simple and short."""

import os
import re
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Groq is optional. If the package isn't installed, we simply won't use it.
try:
    from langchain_groq import ChatGroq  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    ChatGroq = None  # type: ignore[assignment]

try:
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
except ImportError:  # pragma: no cover - older langchain versions
    from langchain.schema import HumanMessage, SystemMessage  # type: ignore[no-redef]
    AIMessage = None  # type: ignore[assignment]
from app.services.supabase_rag import get_rag_service
from app.utils.spelling import correct_spelling, extract_clean_message


def _get_llm():
    """Get LLM - tries Gemini, Groq (if available), then OpenAI."""
    # 1) Gemini / Google
    if key := (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            google_api_key=key,
            temperature=0.7,
        )

    # 2) Groq (optional - only if package and key are available)
    groq_key = os.getenv("GROQ_API_KEY")
    if ChatGroq is not None and groq_key:
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
            groq_api_key=groq_key,
            temperature=0.7,
        )

    # 3) OpenAI
    if key := os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_api_key=key,
            temperature=0.7,
        )
    raise RuntimeError("No LLM API key found. Set GOOGLE_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY")


SYSTEM_PROMPT = """You are Chip, a helpful AI assistant for the Alabama tech community. 

IMPORTANT GUIDELINES:
1. **Context Awareness**: When users say "option 1", "the second one", "number 2", etc., they're referring to items from your previous message. Always maintain context from the conversation.

2. **Out-of-scope questions**: If the user asks about topics that are clearly unrelated to Alabama tech community opportunities, internships, challenges, events, or careers (for example: weather, random trivia, sports scores, general world knowledge), **do NOT answer the question content**. Instead, politely say that you are focused on helping with Alabama tech opportunities, internships, challenges, events, and related career questions, and invite them to ask about those.

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
        # Out-of-scope: explicitly instruct the model NOT to answer the content,
        # only to explain the scope of Chip.
        prompt = (
            f"{conversation_context}\n\n"
            f"User: {user_msg_for_prompt}\n\n"
            "The user's question is OUTSIDE the scope of Chip (not about Alabama tech community "
            "opportunities, internships, challenges, events, or tech careers).\n\n"
            "Politely decline to answer the specific question and instead explain that you are focused on "
            "helping with Alabama tech community opportunities, internships, challenges, events, and related "
            "career support. Invite them to ask about those topics instead. Do NOT provide an actual answer "
            "to the out-of-scope content."
        )
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

        # If the model gives an extremely short or empty answer, use a scoped fallback
        if not reply or len(reply) < 5:
            if is_general_question:
                reply = (
                    "I'm mainly here to help with Alabama tech community opportunities, internships, "
                    "challenges, and events, so I can't answer that in detail."
                )
            else:
                reply = (
                    "I'm having trouble answering that right now, but I can help you find Alabama tech "
                    "opportunities, internships, challenges, and events if you tell me what you're looking for."
                )

        # If the model somehow produced the old generic message in the middle of a conversation,
        # try to regenerate something more contextual instead of repeating it.
        if conversation_history and "I'm here to help" in reply and "What would you like to know" in reply:
            try:
                contextual_prompt = (
                    f"{conversation_context}\n\nUser: {user_msg_for_prompt}\n\n"
                    "Continue the conversation naturally based on the context above. "
                    "Do NOT reset the conversation; respond based on the user's latest message."
                )
                reply = (
                    llm.invoke(
                        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=contextual_prompt)]
                    )
                    .content.strip()
                )
            except Exception:
                # If regeneration fails, keep the existing reply
                pass
    except Exception as e:
        # If the LLM call itself fails, use a clear, domain‑specific fallback instead of a vague reset.
        print(f"LangChain error: {e}")
        if is_general_question:
            reply = (
                "I'm focused on helping with Alabama tech community opportunities, internships, challenges, "
                "and events, so I can't answer that specific question."
            )
        else:
            reply = (
                "Something went wrong while trying to answer that. "
                "I can still help you explore Alabama tech opportunities, internships, challenges, and events "
                "if you tell me what you're interested in."
            )
    
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