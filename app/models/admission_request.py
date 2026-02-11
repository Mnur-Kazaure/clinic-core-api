# app/models/admission_request.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import AdmissionType, AdmissionRequestStatus


class AdmissionRequest(Base):
    __tablename__ = "admission_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    admission_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    admission_type: Mapped[AdmissionType] = mapped_column(
        Enum(AdmissionType, name="admission_type"),
        nullable=False,
    )
    status: Mapped[AdmissionRequestStatus] = mapped_column(
        Enum(AdmissionRequestStatus, name="admission_request_status"),
        nullable=False,
        default=AdmissionRequestStatus.PENDING,
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)

    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    decided_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_admission_requests_id_clinic"),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_admission_requests_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_admission_requests_admission_clinic",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_admission_requests_clinic_id",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "admission_id",
            "clinic_id",
            name="uq_admission_requests_admission_clinic",
        ),
        CheckConstraint(
            "length(reason) >= 3",
            name="ck_admission_requests_reason_length",
        ),
    )
