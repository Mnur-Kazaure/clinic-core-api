# app/models/user.py

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    specialty: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    room_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    availability_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    default_lab_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_lines.id", ondelete="SET NULL"),
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
