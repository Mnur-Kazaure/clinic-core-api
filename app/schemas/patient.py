from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field
from app.shared.enums import Gender


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


class PatientReadSchema(BaseModel):
    """
    Schema returned after patient creation or retrieval.
    """
    id: UUID
    full_name: str
    clinic_id: UUID
    gender: Gender

    class Config:
        from_attributes = True


