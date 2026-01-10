# app/schemas/consultation.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ---------------------------
# Create Consultation
# ---------------------------

class ConsultationCreateRequest(BaseModel):
    visit_id: UUID


# ---------------------------
# Update Consultation
# ---------------------------

class ConsultationUpdateRequest(BaseModel):
    vitals: Optional[str] = None
    presenting_complaints: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------
# Read / Response
# ---------------------------

class ConsultationResponse(BaseModel):
    id: UUID
    visit_id: UUID
    doctor_id: UUID

    vitals: Optional[str]
    presenting_complaints: Optional[str]
    diagnosis: Optional[str]
    notes: Optional[str]

    started_at: datetime
    completed_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
