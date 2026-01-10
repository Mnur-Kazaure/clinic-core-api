# app/schemas/prescription.py
from pydantic import BaseModel, UUID4, Field
from typing import Optional
from datetime import datetime

from app.shared.enums import PrescriptionStatus


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
    reason: Optional[str] = None  # intentionally not persisted (Phase 11)


# -----------------------------
# Response
# -----------------------------

class PrescriptionResponse(BaseModel):
    id: UUID4
    consultation_id: UUID4
    visit_id: UUID4

    drug_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str]

    status: PrescriptionStatus

    prescribed_by: UUID4
    dispensed_by: Optional[UUID4]

    issued_at: datetime
    dispensed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    class Config:
        from_attributes = True