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
    """Generate a reply for Chip without calling an external LLM.

    We keep the same function signature, but implement the behaviour
    deterministically using the Supabase RAG service and simple rules.
    """

    # Normalise and lightly correct the user's message
    cleaned_message = extract_clean_message(user_message)
    corrected_message = correct_spelling(cleaned_message, aggressive=True)
    query = corrected_message or cleaned_message

    # Detect if this is a general (out-of-scope) question
    if _is_general_knowledge_question(query):
        reply = (
            "I'm here to help with Alabama tech community opportunities, internships, "
            "challenges, and events. I can't really answer that question, but if you tell me "
            "what kind of opportunity or challenge you're interested in, I can share options "
            "or next steps."
        )
        return reply, _detect_submission(user_message, context, user_id)

    # Ask the RAG service for relevant opportunities/challenges
    rag = get_rag_service()
    context = rag.get_context_for_query(query)

    # If we didn't get any meaningful context back, tell the user
    if not context or not context.strip() or "No specific context" in context:
        reply = (
            "I wasn't able to find any specific opportunities or challenges that match your request. "
            "You can try asking about \"internships\", \"jobs\", or \"challenges\" in the Alabama tech "
            "community, or reach out to the Innovation Portal team for more details."
        )
        return reply, _detect_submission(user_message, context, user_id)

    # If the user seems to be selecting an option from a previous list
    if _is_selecting_option(query):
        reply = (
            "Got it — it sounds like you're interested in one of the options I shared. "
            "Please reply with the title or a short description of the opportunity or challenge "
            "you're choosing, and I'll help you with the next steps."
        )
        return reply, _detect_submission(user_message, context, user_id)

    # Otherwise, format the context into a friendly list
    lines: list[str] = []
    lowered = query.lower()
    if any(word in lowered for word in ["job", "jobs", "intern", "internship", "opportunit"]):
        lines.append("Here are some Alabama tech opportunities and internships I found:")
    elif "challenge" in lowered:
        lines.append("Here are some Alabama tech challenges that might interest you:")
    else:
        lines.append(
            "Here are some opportunities and challenges from the Alabama tech community that may be relevant:"
        )

    lines.append("")
    lines.append(context)
    lines.append("")
    lines.append(
        "If you're interested in one of these, you can reply with something like "
        "\"I'm interested in option 1\" or mention the title of the opportunity or challenge."
    )

    reply = "\n".join(lines)
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