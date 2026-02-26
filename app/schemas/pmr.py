# app/schemas/pmr.py
from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import MRNStatus, PurposeOfUse, VisitStatus, AdmissionStatus, Gender


class PMRAccessQuery(BaseModel):
    purpose_of_use: PurposeOfUse
    justification: str = Field(min_length=2)
    break_glass: bool = False


class PMRClinicalHistoryPage(BaseModel):
    limit: int
    next_cursor: str | None = None
    has_more: bool
    generated_at: datetime


class PMRNotePreview(BaseModel):
    text: str | None = None
    max_len: int = 200
    truncated: bool = False


class PMRConsultationSummary(BaseModel):
    consultation_id: UUID
    created_at: datetime
    completed_at: datetime | None = None
    clinician_id: UUID
    presenting_complaint_preview: str | None = None
    diagnosis_summary: str | None = None
    plan_preview: str | None = None
    note_preview: PMRNotePreview


class PMRConsultationSection(BaseModel):
    exists: bool
    missing_reason: str | None = None
    item: PMRConsultationSummary | None = None


class PMRDrugSummary(BaseModel):
    name: str
    dose: str | None = None
    frequency: str | None = None
    duration: str | None = None


class PMRPrescriptionSummary(BaseModel):
    prescription_id: UUID
    created_at: datetime
    clinician_id: UUID
    status: str
    drugs: list[PMRDrugSummary]


class PMRPrescriptionsSection(BaseModel):
    exists: bool
    missing_reason: str | None = None
    count: int = 0
    items: list[PMRPrescriptionSummary] = Field(default_factory=list)


class PMRLabTestSummary(BaseModel):
    code: str | None = None
    name: str


class PMRLabResultSummary(BaseModel):
    test_name: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None


class PMRLabRequestSummary(BaseModel):
    lab_request_id: UUID
    created_at: datetime
    ordered_by_id: UUID
    status: str
    tests: list[PMRLabTestSummary]
    special_instructions: str | None = None
    results_available: bool = False
    results_summary: list[PMRLabResultSummary] = Field(default_factory=list)


class PMRLabsSection(BaseModel):
    exists: bool
    missing_reason: str | None = None
    count: int = 0
    requests: list[PMRLabRequestSummary] = Field(default_factory=list)


class PMRVisitClinicalSections(BaseModel):
    consultation: PMRConsultationSection
    prescriptions: PMRPrescriptionsSection
    labs: PMRLabsSection


class PMRVisitClinicalHistory(BaseModel):
    visit_id: UUID
    visit_status: VisitStatus
    visit_started_at: datetime
    visit_closed_at: datetime | None = None
    assigned_doctor_id: UUID | None = None
    sections: PMRVisitClinicalSections


class PMRMrnResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    mrn: str
    status: MRNStatus
    issued_at: datetime
    issued_by: UUID
    check_digit: str
    retired_at: datetime | None = None
    retire_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PMRVisitSummary(BaseModel):
    id: UUID
    status: VisitStatus
    started_at: datetime
    completed_at: datetime | None = None
    assigned_doctor_id: UUID

    model_config = ConfigDict(from_attributes=True)


class PMRAdmissionSummary(BaseModel):
    id: UUID
    status: AdmissionStatus
    admitted_at: datetime
    discharged_at: datetime | None = None
    cancelled_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PMRFollowUpTimelineItem(BaseModel):
    event_type: str
    occurred_at: datetime
    follow_up_id: UUID | None = None
    chronic_recall_id: UUID | None = None
    detail: str | None = None


class PMRResponse(BaseModel):
    patient_id_requested: UUID
    patient_id_canonical: UUID
    access_log_id: UUID
    identity_state: str
    full_name: str
    date_of_birth: date
    gender: Gender
    phone_number: str | None = None
    address: str | None = None
    occupation: str | None = None
    active_mrn: PMRMrnResponse | None
    retired_mrns: list[PMRMrnResponse]
    identity_closure_ids: list[UUID]
    visits: list[PMRVisitSummary]
    admissions: list[PMRAdmissionSummary]
    effective_detail_level: str = "SUMMARY"
    detail_level_downgraded: bool = False
    clinical_history_page: PMRClinicalHistoryPage
    clinical_history: list[PMRVisitClinicalHistory] = Field(default_factory=list)
    follow_up_timeline: list[PMRFollowUpTimelineItem] = Field(default_factory=list)


class MRNIssueResponse(BaseModel):
    mrn: PMRMrnResponse
