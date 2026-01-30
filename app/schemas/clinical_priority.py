# app/schemas/clinical_priority.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import ClinicalPriorityLevel, ClinicalPrioritySource


class ClinicalPriorityCreateRequest(BaseModel):
    level: ClinicalPriorityLevel
    source: ClinicalPrioritySource
    reason: str = Field(min_length=3)


class ClinicalPriorityResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    visit_id: UUID
    patient_id: UUID
    level: ClinicalPriorityLevel
    source: ClinicalPrioritySource
    reason: str
    set_by: UUID
    set_at: datetime

    model_config = ConfigDict(from_attributes=True)
