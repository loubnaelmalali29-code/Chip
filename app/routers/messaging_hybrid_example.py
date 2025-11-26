"""Example of hybrid approach - combining fast regex with LLM for complex cases."""

from app.utils.spelling import correct_spelling, extract_clean_message

async def _process_input_intelligently(raw_text: str) -> tuple[str, str]:
    """
    Hybrid approach:
    1. Fast regex correction for common typos (instant, free)
    2. LLM correction only if text looks complex/needs grammar help
    3. Get RAG context with corrected text
    """
    # Step 1: Fast regex correction (our implementation)
    cleaned_text = extract_clean_message(raw_text)
    corrected_text = correct_spelling(cleaned_text)
    
    # Step 2: Check if we need LLM help
    # Only use LLM if:
    # - Text is long (might have complex grammar issues)
    # - Regex didn't change anything but text looks problematic
    # - User explicitly needs grammar correction
    
    needs_llm_correction = (
        len(corrected_text) > 100 or  # Long messages might need grammar help
        (corrected_text == cleaned_text and len(corrected_text.split()) > 10)  # Complex but unchanged
    )
    
    if needs_llm_correction:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            
            llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
            messages = [
                SystemMessage(content=(
                    "You are a text cleaner. Correct spelling and grammar errors. "
                    "Keep the meaning. If text is correct, return it as-is. "
                    "Output ONLY the corrected text."
                )),
                HumanMessage(content=corrected_text)
            ]
            
            result = await llm.ainvoke(messages)
            final_text = result.content.strip()
            
            if final_text and len(final_text) > 5:  # Safety check
                corrected_text = final_text
        except Exception as e:
            print(f"LLM correction failed ({e}), using regex-corrected text")
            # Fall back to regex-corrected text
    
    # Step 3: Get RAG context with corrected text
    try:
        from app.services.supabase_rag import get_rag_service
        rag_service = get_rag_service()
        context = rag_service.get_context_for_query(corrected_text)
    except Exception as e:
        print(f"RAG service failed ({e})")
        context = ""
    
    # Step 4: Add general Q&A instruction if context is empty
    if not context or "No specific context" in context:
        general_instruction = (
            "\n\n[Note: If the user's question isn't in the database context above, "
            "answer helpfully using your general knowledge. Be conversational and helpful.]"
        )
        context = context + general_instruction
    
    return corrected_text, context



