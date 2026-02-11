# app/schemas/patient.py
from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field, ConfigDict
from app.shared.enums import Gender, IdentityState, BillingReasonCode


class PatientCreateSchema(BaseModel):
    """
    Schema used when creating a new patient.
    """
    full_name: str = Field(..., min_length=2)
    date_of_birth: date
    gender: Gender
    phone_number: str
    address: str
    occupation: str
    identity_state: IdentityState | None = None
    created_reason: str | None = Field(default=None, min_length=3)
    registration_payment_method: BillingReasonCode | None = None
    registration_payment_reference: str | None = None


class PatientReadSchema(BaseModel):
    """
    Schema returned after patient creation or retrieval.
    Reception requires this payload to confirm identity and contact details.
    """
    id: UUID
    clinic_id: UUID
    full_name: str
    date_of_birth: date
    gender: Gender
    phone_number: str
    address: str
    occupation: str
    patient_mrn: str | None = None
    identity_state: IdentityState | None = None
    created_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)
