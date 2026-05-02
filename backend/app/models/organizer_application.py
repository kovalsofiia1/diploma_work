from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OrganizerApplicationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OrganizerApplication(Base):
    __tablename__ = "organizer_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(64), nullable=False)
    motivation: Mapped[str] = mapped_column(Text, nullable=False)
    experience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[OrganizerApplicationStatus] = mapped_column(
        SAEnum(OrganizerApplicationStatus),
        default=OrganizerApplicationStatus.pending,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
