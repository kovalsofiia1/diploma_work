from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("ticket_id", name="uq_tickets_ticket_id"),
        UniqueConstraint("code", name="uq_tickets_code"),
        # Uniqueness of seat within an event (if seat_id is provided)
        UniqueConstraint("event_id", "seat_id", name="uq_tickets_event_seat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Public identifiers
    ticket_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # References
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    # Seat metadata
    seat_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    seat: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Integrity and blockchain (README-conformant)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    ticket_hash: Mapped[str] = mapped_column(String(66), nullable=False, index=True)  # 0x + 64 hex
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True, index=True)  # 0x + 64 hex
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # reserved | pending_onchain | confirmed_onchain | failed_onchain | used
    status: Mapped[str] = mapped_column(String(32), default="reserved", nullable=False)

    # Back-compat fields (kept; can be removed later)
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


