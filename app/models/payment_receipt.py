import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import BillingReasonCode


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    visit_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    cashier_pay_point_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    receipt_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    total_amount_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    payment_method: Mapped[BillingReasonCode] = mapped_column(
        Enum(BillingReasonCode, name="billing_reason_code"),
        nullable=False,
    )

    external_ref: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    collected_by: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_payment_receipts_id_clinic"),
        UniqueConstraint(
            "clinic_id",
            "receipt_number",
            name="uq_payment_receipts_clinic_receipt",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_payment_receipts_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_payment_receipts_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_payment_receipts_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["cashier_pay_point_id"],
            ["cashier_pay_points.id"],
            name="fk_payment_receipts_cashier_pay_point",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["collected_by"],
            ["users.id"],
            name="fk_payment_receipts_collected_by",
        ),
    )
