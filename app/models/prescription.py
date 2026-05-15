# app/models/prescription.py
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    ForeignKey,
    Enum,
    DateTime,
    CheckConstraint,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import (
    PharmacyExceptionAuthorizationType,
    PharmacyPrescriptionWorkflowStatus,
    PrescriptionStatus,
    RecordStatus,
)


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # 🔒 Ownership
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consultations.id", ondelete="RESTRICT"),
        nullable=False,
    )

    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="RESTRICT"),
        nullable=False,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )

    prescribed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    dispensed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    billing_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("billing_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    pharmacy_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pharmacy_catalog_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    assigned_dispensing_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_lines.id", ondelete="SET NULL"),
        nullable=True,
    )

    assigned_cashier_pay_point_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cashier_pay_points.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 💊 Medication payload
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    duration: Mapped[str] = mapped_column(String(50), nullable=False)
    instructions: Mapped[str | None] = mapped_column(String(500))
    quantity_prescribed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    quantity_dispensed_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    quantity_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # 📌 Lifecycle
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus, name="prescription_status"),
        nullable=False,
    )

    workflow_status: Mapped[PharmacyPrescriptionWorkflowStatus] = mapped_column(
        Enum(
            PharmacyPrescriptionWorkflowStatus,
            name="pharmacy_prescription_workflow_status",
        ),
        nullable=False,
        default=PharmacyPrescriptionWorkflowStatus.ASSIGNED,
        server_default=PharmacyPrescriptionWorkflowStatus.ASSIGNED.value,
    )

    exception_authorization_type: Mapped[PharmacyExceptionAuthorizationType] = mapped_column(
        Enum(
            PharmacyExceptionAuthorizationType,
            name="pharmacy_exception_authorization_type",
        ),
        nullable=False,
        default=PharmacyExceptionAuthorizationType.NONE,
        server_default=PharmacyExceptionAuthorizationType.NONE.value,
    )

    exception_authorized_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    exception_authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    record_status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"),
        nullable=False,
        default=RecordStatus.DRAFT,
    )

    void_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    dispensed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    externally_fulfilled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    __table_args__ = (
        # 🔒 State → timestamp integrity
        CheckConstraint(
            "(status != 'DISPENSED') OR dispensed_at IS NOT NULL",
            name="ck_prescription_dispensed_requires_timestamp",
        ),
        CheckConstraint(
            "(status != 'CANCELLED') OR cancelled_at IS NOT NULL",
            name="ck_prescription_cancelled_requires_timestamp",
        ),
        CheckConstraint(
            "(status != 'EXTERNALLY_FULFILLED') OR externally_fulfilled_at IS NOT NULL",
            name="ck_prescription_external_requires_timestamp",
        ),
        CheckConstraint(
            "quantity_prescribed > 0",
            name="ck_prescription_quantity_prescribed_positive",
        ),
        CheckConstraint(
            "quantity_dispensed_total >= 0",
            name="ck_prescription_quantity_dispensed_total_non_negative",
        ),
        CheckConstraint(
            "quantity_remaining >= 0",
            name="ck_prescription_quantity_remaining_non_negative",
        ),
        CheckConstraint(
            "quantity_dispensed_total <= quantity_prescribed",
            name="ck_prescription_quantity_dispensed_total_lte_prescribed",
        ),
        CheckConstraint(
            "quantity_remaining <= quantity_prescribed",
            name="ck_prescription_quantity_remaining_lte_prescribed",
        ),
    )
