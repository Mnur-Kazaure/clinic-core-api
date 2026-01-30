# app/schemas/identity.py
from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    IdentityCaseType,
    IdentityCaseStatus,
    Gender,
    IdentityEvidenceType,
    IdentityApprovalDecision,
)


class ProvisionalPatientRequest(BaseModel):
    full_name: str | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    phone_number: str | None = None
    address: str | None = None
    occupation: str | None = None
    created_reason: str | None = None


class IdentityCaseCreateRequest(BaseModel):
    case_type: IdentityCaseType
    primary_patient_id: UUID
    target_patient_id: UUID | None = None
    reason: str = Field(min_length=3)


class IdentityCaseResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    case_type: IdentityCaseType
    status: IdentityCaseStatus
    created_by: UUID
    created_at: datetime
    reason: str
    primary_patient_id: UUID
    target_patient_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class IdentityEvidenceCreateRequest(BaseModel):
    evidence_type: IdentityEvidenceType
    ref: str
    notes: str | None = None


class IdentityApprovalRequest(BaseModel):
    decision: IdentityApprovalDecision
    decision_reason: str = Field(min_length=3)


class IdentityRollbackRequest(BaseModel):
    reason: str = Field(min_length=3)
