from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ChatRequestLog(Base):
    """One row per accepted chat request; the rate limiter counts rows inside a sliding window."""

    __tablename__ = "chat_request_log"
    __table_args__ = (Index("ix_chat_request_log_key_time", "client_key", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # "user:<id>" for a verified token, "ip:<address>" otherwise
    client_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
