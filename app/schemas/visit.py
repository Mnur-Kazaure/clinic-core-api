# app/schemas/visit.py
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal
from uuid import UUID
from datetime import datetime

from app.shared.enums import (
    ClinicalPriorityLevel,
    VisitOverrideReasonCode,
    VisitServiceLine,
    VisitStatus,
    VisitTriageState,
)


# ---------------------------
# Core Visit Response
# ---------------------------

class VisitResponse(BaseModel):
    id: UUID
    patient_id: UUID
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    consultation_status: Optional[str] = None
    intake_emergency_flag: Optional[bool] = None
    intake_emergency_reason: Optional[str] = None
    intake_emergency_set_at: Optional[datetime] = None
    clinic_id: UUID
    status: VisitStatus
    service_line: VisitServiceLine
    service_line_id: Optional[UUID] = None
    triage_state: VisitTriageState = VisitTriageState.PENDING
    triage_acuity: Optional[ClinicalPriorityLevel] = None
    triaged_at: Optional[datetime] = None
    triaged_by: Optional[UUID] = None
    assigned_doctor_id: Optional[UUID]
    linked_follow_up_id: Optional[UUID] = None
    has_active_admission: Optional[bool] = None
    version: int


    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------
# Transition Request
# ---------------------------

class VisitTransitionRequest(BaseModel):
    to_status: VisitStatus
    mode: Literal["normal", "override"] = "normal"
    override_reason_code: Optional[VisitOverrideReasonCode] = None
    override_reason_text: Optional[str] = None
    expected_version: int


class VisitReassignRequest(BaseModel):
    assigned_doctor_id: UUID
    expected_version: int
    service_line: Optional[VisitServiceLine] = None
    reason: Optional[str] = Field(default=None, min_length=2, max_length=200)


class VisitIntakeFlagRequest(BaseModel):
    flagged: bool
    reason: str = Field(..., min_length=3)


# ---------------------------
# Allowed Transitions
# ---------------------------

class AllowedTransitionsResponse(BaseModel):
    allowed: List[VisitStatus]


# ---------------------------
# Timeline
# ---------------------------

class VisitTimelineEvent(BaseModel):
    id: UUID
    from_status: VisitStatus
    to_status: VisitStatus
    changed_by: UUID
    created_at: datetime


class VisitTimelineResponse(BaseModel):
    visit_id: UUID
    timeline: List[VisitTimelineEvent]

# ---------------------------
# Create Visit
# ---------------------------

class VisitCreateRequest(BaseModel):
    patient_id: UUID
    assigned_doctor_id: Optional[UUID] = None
    service_line_id: Optional[UUID] = None
    service_line: VisitServiceLine = VisitServiceLine.OPD
    linked_follow_up_id: Optional[UUID] = None


class VisitCreateResponse(VisitResponse):
    pass
