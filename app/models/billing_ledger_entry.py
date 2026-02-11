# app/models/billing_ledger_entry.py
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    Text,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import BillingEntryType, BillingReasonCode


class BillingLedgerEntry(Base):
    __tablename__ = "billing_ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    admission_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    entry_type: Mapped[BillingEntryType] = mapped_column(
        Enum(BillingEntryType, name="billing_entry_type"),
        nullable=False,
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason_code: Mapped[BillingReasonCode] = mapped_column(
        Enum(BillingReasonCode, name="billing_reason_code"),
        nullable=False,
    )
    charge_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_entry_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_billing_ledger_id_clinic"),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_billing_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_billing_visit_clinic",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_billing_admission_clinic",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["related_entry_id", "clinic_id"],
            ["billing_ledger_entries.id", "billing_ledger_entries.clinic_id"],
            name="fk_billing_related_entry",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_billing_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_billing_actor",
        ),
        CheckConstraint(
            "length(description) >= 3",
            name="ck_billing_description_length",
        ),
        CheckConstraint(
            "amount_minor <> 0",
            name="ck_billing_amount_nonzero",
        ),
        CheckConstraint(
            "(entry_type = 'CHARGE' AND amount_minor > 0) OR "
            "(entry_type = 'PAYMENT' AND amount_minor < 0) OR "
            "(entry_type = 'REFUND' AND amount_minor > 0) OR "
            "(entry_type = 'WRITE_OFF' AND amount_minor < 0) OR "
            "(entry_type IN ('ADJUSTMENT','REVERSAL') AND amount_minor <> 0)",
            name="ck_billing_entry_sign",
        ),
        CheckConstraint(
            "(entry_type IN ('PAYMENT','REFUND','REVERSAL')) OR "
            "(entry_type IN ('CHARGE','ADJUSTMENT','WRITE_OFF') AND (visit_id IS NOT NULL OR admission_id IS NOT NULL)) OR "
            "(entry_type = 'CHARGE' AND reason_code = 'REGISTRATION_FEE')",
            name="ck_billing_entry_context",
        ),
        CheckConstraint(
            "(entry_type = 'REVERSAL' AND related_entry_id IS NOT NULL) OR "
            "(entry_type != 'REVERSAL' AND related_entry_id IS NULL)",
            name="ck_billing_reversal_link",
        ),
    )
