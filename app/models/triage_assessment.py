import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import (
    ClinicalPriorityLevel,
    TriageComplaintSeverity,
    TriageFallbackReasonCode,
    TriageFinalizeAction,
    TriageMissingVitalReasonCode,
    TriageScaleVersion,
)


class TriageAssessment(Base):
    __tablename__ = "triage_assessments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    assessed_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    assessed_by_role: Mapped[str] = mapped_column(String(50), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    finalized_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    finalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    triage_scale_version: Mapped[TriageScaleVersion] = mapped_column(
        Enum(TriageScaleVersion, name="triage_scale_version"),
        nullable=False,
        default=TriageScaleVersion.PHC_V1,
        server_default=TriageScaleVersion.PHC_V1.value,
    )
    acuity_level: Mapped[ClinicalPriorityLevel] = mapped_column(
        Enum(ClinicalPriorityLevel, name="clinical_priority_level"),
        nullable=False,
    )
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False)
    complaint_severity: Mapped[TriageComplaintSeverity] = mapped_column(
        Enum(TriageComplaintSeverity, name="triage_complaint_severity"),
        nullable=False,
    )
    triage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    danger_sign_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    temp_c: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    pulse_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rr_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sbp_mmhg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dbp_mmhg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spo2_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_vitals_reason_code: Mapped[TriageMissingVitalReasonCode | None] = mapped_column(
        Enum(
            TriageMissingVitalReasonCode,
            name="triage_missing_vital_reason_code",
        ),
        nullable=True,
    )

    is_doctor_fallback: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    fallback_reason_code: Mapped[TriageFallbackReasonCode | None] = mapped_column(
        Enum(TriageFallbackReasonCode, name="triage_fallback_reason_code"),
        nullable=True,
    )
    fallback_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    triage_finalize_action: Mapped[TriageFinalizeAction] = mapped_column(
        Enum(TriageFinalizeAction, name="triage_finalize_action"),
        nullable=False,
        default=TriageFinalizeAction.QUEUE_FOR_CONSULTATION,
        server_default=TriageFinalizeAction.QUEUE_FOR_CONSULTATION.value,
    )
    referred_facility: Mapped[str | None] = mapped_column(String(200), nullable=True)
    referral_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    supersedes_assessment_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correction_reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    correction_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_triage_assessment_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_triage_assessment_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_triage_assessment_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["assessed_by"],
            ["users.id"],
            name="fk_triage_assessment_assessed_by",
        ),
        ForeignKeyConstraint(
            ["finalized_by"],
            ["users.id"],
            name="fk_triage_assessment_finalized_by",
        ),
        ForeignKeyConstraint(
            ["supersedes_assessment_id"],
            ["triage_assessments.id"],
            name="fk_triage_assessment_supersedes",
        ),
    )
