# app/schemas/admission.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import AdmissionType, AdmissionStatus


class BreakGlassInfo(BaseModel):
    break_glass: bool = False
    purpose_of_use: str | None = None
    reason: str | None = None


class AdmissionCreateRequest(BreakGlassInfo):
    patient_id: UUID
    admission_type: AdmissionType


class AdmissionCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3)


class AdmissionResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    admission_type: AdmissionType
    status: AdmissionStatus
    admitted_at: datetime
    discharged_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
