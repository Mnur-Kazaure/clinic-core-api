import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CashierShift(Base):
    __tablename__ = "cashier_shifts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    cashier_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    opening_float_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    closing_cash_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    closing_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    reconciled_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_cashier_shifts_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["cashier_id"],
            ["users.id"],
            name="fk_cashier_shifts_cashier",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["reconciled_by"],
            ["users.id"],
            name="fk_cashier_shifts_reconciled_by",
        ),
        CheckConstraint(
            "status IN ('OPEN','CLOSED','RECONCILED')",
            name="ck_cashier_shifts_status",
        ),
        CheckConstraint(
            "opening_float_minor >= 0",
            name="ck_cashier_shifts_opening_float_non_negative",
        ),
    )
