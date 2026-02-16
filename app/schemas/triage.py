from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    ClinicalPriorityLevel,
    TriageAssessmentRecordStatus,
    TriageComplaintSeverity,
    TriageFallbackReasonCode,
    TriageFinalizeAction,
    TriageMissingVitalReasonCode,
    TriageScaleVersion,
    VisitStatus,
)


class TriageFinalizeRequest(BaseModel):
    expected_version: int = Field(..., ge=1)
    action: TriageFinalizeAction = TriageFinalizeAction.QUEUE_FOR_CONSULTATION
    acuity_level: ClinicalPriorityLevel
    chief_complaint: str = Field(..., min_length=3, max_length=500)
    complaint_severity: TriageComplaintSeverity
    triage_note: str | None = Field(default=None, max_length=2000)
    danger_sign_codes: list[str] = Field(default_factory=list, max_length=30)

    temp_c: float | None = Field(default=None, ge=20, le=50)
    pulse_bpm: int | None = Field(default=None, ge=10, le=300)
    rr_bpm: int | None = Field(default=None, ge=2, le=100)
    sbp_mmhg: int | None = Field(default=None, ge=40, le=350)
    dbp_mmhg: int | None = Field(default=None, ge=20, le=220)
    spo2_pct: int | None = Field(default=None, ge=20, le=100)
    missing_vitals_reason_code: TriageMissingVitalReasonCode | None = None

    is_doctor_fallback: bool = False
    fallback_reason_code: TriageFallbackReasonCode | None = None
    fallback_reason_text: str | None = Field(default=None, max_length=500)

    referred_facility: str | None = Field(default=None, max_length=200)
    referral_reason: str | None = Field(default=None, max_length=500)


class TriageSupersedeRequest(TriageFinalizeRequest):
    correction_reason_code: str = Field(..., min_length=2, max_length=50)
    correction_reason_text: str | None = Field(default=None, max_length=500)


class TriageDraftRequest(TriageFinalizeRequest):
    pass


class TriageSignRequest(BaseModel):
    expected_version: int = Field(..., ge=1)


class TriageAssessmentResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    visit_id: UUID
    patient_id: UUID
    assessed_by: UUID
    assessed_by_role: str
    assessed_at: datetime
    record_status: TriageAssessmentRecordStatus
    finalized_by: UUID
    finalized_at: datetime
    triage_scale_version: TriageScaleVersion
    acuity_level: ClinicalPriorityLevel
    chief_complaint: str
    complaint_severity: TriageComplaintSeverity
    triage_note: str | None = None
    danger_sign_codes: list[str] | None = None
    temp_c: float | None = None
    pulse_bpm: int | None = None
    rr_bpm: int | None = None
    sbp_mmhg: int | None = None
    dbp_mmhg: int | None = None
    spo2_pct: int | None = None
    missing_vitals_reason_code: TriageMissingVitalReasonCode | None = None
    is_doctor_fallback: bool
    fallback_reason_code: TriageFallbackReasonCode | None = None
    fallback_reason_text: str | None = None
    triage_finalize_action: TriageFinalizeAction
    referred_facility: str | None = None
    referral_reason: str | None = None
    supersedes_assessment_id: UUID | None = None
    superseded_at: datetime | None = None
    correction_reason_code: str | None = None
    correction_reason_text: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TriageFinalizeResponse(BaseModel):
    triage_assessment: TriageAssessmentResponse
    visit_id: UUID
    visit_status: VisitStatus
    visit_version: int


class TriageDraftResponse(BaseModel):
    triage_assessment: TriageAssessmentResponse
    visit_id: UUID
    visit_status: VisitStatus
    visit_version: int
