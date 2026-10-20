from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat_message
from app.services.llm_client import LLMClient, LLMUnavailableError, get_llm_client

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=ChatResponse)
async def send_message(
    req: ChatRequest,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> ChatResponse:
    """Public, stateless: one question in, one answer out."""
    try:
        return await handle_chat_message(db, llm, req.message.strip())
    except LLMUnavailableError:
        # The rest of the site (regular filters) keeps working; the widget shows this message.
        raise HTTPException(
            status_code=503,
            detail={
                "code": "llm_unavailable",
                "message": "Чат-бот тимчасово недоступний. Скористайтеся фільтрами пошуку.",
            },
        )
