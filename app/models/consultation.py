# app/models/consultation.py
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Consultation(Base):
    __tablename__ = "consultations"

    __table_args__ = (
        UniqueConstraint("visit_id", name="uq_consultation_visit"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
    )

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ───────── Clinical Content (MVP) ─────────

    vitals: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    presenting_complaints: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    diagnosis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Optional relationships (read-only usage later)
    visit = relationship("Visit", lazy="joined")