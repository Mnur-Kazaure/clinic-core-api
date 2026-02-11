# app/models/visit_status_history.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Enum, ForeignKey, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import VisitStatus


class VisitStatusHistory(Base):
    __tablename__ = "visit_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus),
        nullable=False,
    )

    to_status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus),
        nullable=False,
    )

    changed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    # manual | auto | override | reopen (stored as text for portability)
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
    )

    # Optional override context
    reason_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    reason_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    pending_labs_count_snapshot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    unfulfilled_prescriptions_count_snapshot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
