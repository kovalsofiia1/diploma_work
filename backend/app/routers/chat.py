from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_security import RateLimited, check_and_record, client_key
from app.services.chat_service import handle_chat_message
from app.services.llm_client import LLMClient, LLMUnavailableError, get_llm_client

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=ChatResponse)
async def send_message(
    req: ChatRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> ChatResponse:
    """Public, stateless: one question in, one answer out. Rate limited per client (20 per hour by default)."""
    limit = get_settings().chat_rate_limit_per_hour
    try:
        state = check_and_record(db, client_key(request))
    except RateLimited as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "Забагато запитів до чат-бота. Спробуйте пізніше.",
                "retry_after_seconds": exc.retry_after_seconds,
            },
            headers={
                "Retry-After": str(exc.retry_after_seconds),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
    response.headers["X-RateLimit-Limit"] = str(state.limit)
    response.headers["X-RateLimit-Remaining"] = str(state.remaining)

    try:
        return await handle_chat_message(db, llm, req.message)
    except LLMUnavailableError:
        # The rest of the site (regular filters) keeps working; the widget shows this message.
        raise HTTPException(
            status_code=503,
            detail={
                "code": "llm_unavailable",
                "message": "Чат-бот тимчасово недоступний. Скористайтеся фільтрами пошуку.",
            },
        )
