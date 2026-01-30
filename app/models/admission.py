# app/models/admission.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import AdmissionType, AdmissionStatus


class Admission(Base):
    __tablename__ = "admissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    admission_type: Mapped[AdmissionType] = mapped_column(
        Enum(AdmissionType, name="admission_type"),
        nullable=False,
    )
    status: Mapped[AdmissionStatus] = mapped_column(
        Enum(AdmissionStatus, name="admission_status"),
        nullable=False,
    )
    admitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    discharged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_admissions_id_clinic"),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_admissions_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_admissions_clinic_id",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(status != 'DISCHARGED') OR (discharged_at IS NOT NULL)",
            name="ck_admissions_discharged_at",
        ),
        CheckConstraint(
            "(status != 'CANCELLED') OR (cancelled_at IS NOT NULL AND cancel_reason IS NOT NULL)",
            name="ck_admissions_cancelled_at_reason",
        ),
        CheckConstraint(
            "(status != 'ACTIVE') OR (discharged_at IS NULL AND cancelled_at IS NULL)",
            name="ck_admissions_active_no_end",
        ),
    )
