# app/schemas/prescription.py
from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.shared.enums import (
    PrescriptionFulfillmentType,
    PrescriptionStatus,
    UserRole,
)


# -----------------------------
# Issue Prescription
# -----------------------------

class PrescriptionCreateRequest(BaseModel):
    consultation_id: UUID4

    drug_name: str = Field(..., min_length=1)
    dosage: str = Field(..., min_length=1)
    frequency: str = Field(..., min_length=1)
    duration: str = Field(..., min_length=1)

    instructions: Optional[str] = None


# -----------------------------
# Dispense Prescription
# -----------------------------

class PrescriptionDispenseRequest(BaseModel):
    pharmacist_id: UUID4
    quantity: Optional[int] = None  # intentionally unused (Phase 11)


# -----------------------------
# Cancel Prescription
# -----------------------------

class PrescriptionCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3)


# -----------------------------
# Response
# -----------------------------

class PrescriptionResponse(BaseModel):
    id: UUID4
    consultation_id: UUID4
    visit_id: UUID4
    patient_id: Optional[UUID4] = None
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None

    drug_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str]

    status: PrescriptionStatus

    prescribed_by: UUID4
    prescribed_by_name: Optional[str] = None
    prescribed_by_role: Optional[UserRole] = None
    dispensed_by: Optional[UUID4]
    dispensed_by_name: Optional[str] = None
    dispensed_by_role: Optional[UserRole] = None

    issued_at: datetime
    dispensed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    fulfillment_type: Optional[PrescriptionFulfillmentType] = None
    fulfillment_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
