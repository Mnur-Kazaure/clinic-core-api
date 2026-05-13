# app/models/attendance_log.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # e.g., "PUNCH_IN", "PUNCH_OUT"
    punch_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    punched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # External ID from the biometric hardware
    hardware_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Where the punch happened (e.g., "MAIN_ENTRANCE")
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Full raw payload from device if needed
    device_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
