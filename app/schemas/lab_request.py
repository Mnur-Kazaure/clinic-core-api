# app/schemas/lab_request.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from app.shared.enums import LabRequestStatus


class LabRequestCreate(BaseModel):
    visit_id: UUID
    test_name: str
    special_instructions: str | None = None


class LabRequestResponse(BaseModel):
    id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    test_name: str
    special_instructions: str | None = None
    status: LabRequestStatus
    requested_by: UUID
    requested_by_name: str | None = None
    requested_by_role: str | None = None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
