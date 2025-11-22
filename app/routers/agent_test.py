from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.langchain_agent import generate_reply_with_langchain
from app.services.supabase_rag import get_rag_service


router = APIRouter(prefix="/test", tags=["test"])

# Initialize RAG service
_rag_service = get_rag_service()


class AgentTestRequest(BaseModel):
    message: str


@router.post("/agent")
async def test_agent(req: AgentTestRequest):
    """Test the LangChain agent."""
    context = _rag_service.get_context_for_query(req.message)
    reply_text, submission_data = generate_reply_with_langchain(
        user_message=req.message,
        context=context,
        user_id=None,
    )
    return {
        "ok": True,
        "reply": reply_text,
        "submission_detected": submission_data is not None,
    }
