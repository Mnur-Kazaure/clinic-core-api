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


class BillingRefund(Base):
    __tablename__ = "billing_refunds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    receipt_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    billing_item_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROCESSED")

    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    approved_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    processed_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_billing_refunds_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["receipt_id", "clinic_id"],
            ["payment_receipts.id", "payment_receipts.clinic_id"],
            name="fk_billing_refunds_receipt",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["billing_item_id", "clinic_id"],
            ["billing_items.id", "billing_items.clinic_id"],
            name="fk_billing_refunds_billing_item",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_billing_refunds_requested_by",
        ),
        ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_billing_refunds_approved_by",
        ),
        ForeignKeyConstraint(
            ["processed_by"],
            ["users.id"],
            name="fk_billing_refunds_processed_by",
        ),
        CheckConstraint(
            "amount_minor > 0",
            name="ck_billing_refunds_amount_positive",
        ),
        CheckConstraint(
            "status IN ('REQUESTED','PROCESSED','REJECTED')",
            name="ck_billing_refunds_status",
        ),
    )
