# app/schemas/admission.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    AdmissionType,
    AdmissionStatus,
    AdmissionRequestStatus,
    AdmissionDischargeDisposition,
)


class BreakGlassInfo(BaseModel):
    break_glass: bool = False
    purpose_of_use: str | None = None
    reason: str | None = None


class AdmissionCreateRequest(BreakGlassInfo):
    patient_id: UUID
    admission_type: AdmissionType


class AdmissionCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3)

class AdmissionDischargeRequest(BaseModel):
    disposition: AdmissionDischargeDisposition = AdmissionDischargeDisposition.HOME
    transferred_to_facility: str | None = Field(default=None, min_length=3)
    death_pronounced_at: datetime | None = None
    discharge_notes: str | None = Field(default=None, min_length=3)


class AdmissionResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    admission_type: AdmissionType
    status: AdmissionStatus
    admitted_at: datetime
    discharged_at: datetime | None
    discharge_disposition: AdmissionDischargeDisposition | None = None
    transferred_to_facility: str | None = None
    death_pronounced_at: datetime | None = None
    discharge_notes: str | None = None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdmissionRequestCreateRequest(BaseModel):
    patient_id: UUID
    admission_type: AdmissionType
    reason: str = Field(..., min_length=3)


class AdmissionRequestDecisionRequest(BaseModel):
    reason: str = Field(..., min_length=3)


class AdmissionRequestResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    admission_type: AdmissionType
    status: AdmissionRequestStatus
    reason: str
    requested_by: UUID
    requested_at: datetime
    decided_by: UUID | None
    decided_at: datetime | None
    decision_reason: str | None
    admission_id: UUID | None = None
    has_active_bed_assignment: bool = False
    current_bed_id: UUID | None = None
    current_bed_label: str | None = None

    model_config = ConfigDict(from_attributes=True)
