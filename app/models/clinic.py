# app/models/clinic.py

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    timezone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    billing_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="NGN",
    )

    registration_fee_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=100000,
    )

    registration_fee_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    monthly_revenue_target_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
