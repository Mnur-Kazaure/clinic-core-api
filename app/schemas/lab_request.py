# app/schemas/lab_request.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.shared.enums import LabRequestStatus


class LabRequestCreate(BaseModel):
    visit_id: UUID
    test_name: str


class LabRequestResponse(BaseModel):
    id: UUID
    visit_id: UUID
    test_name: str
    status: LabRequestStatus
    requested_by: UUID
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True