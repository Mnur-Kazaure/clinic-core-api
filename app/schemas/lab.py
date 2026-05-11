# app/schemas/lab.py

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime

from app.shared.enums import LabResultLifecycleStatus, LabRequestStatus, VisitStatus


class LabResultCreate(BaseModel):
    result_value: str = Field(min_length=1)
    result_unit: str | None = None
    reference_range: str | None = None


class LabResultResponse(BaseModel):
    id: UUID
    lab_request_id: UUID
    result_value: str
    result_unit: str | None = None
    reference_range: str | None = None
    technician_id: UUID
    status: LabResultLifecycleStatus | None = None
    entered_by: UUID | None = None
    entered_at: datetime | None = None
    verified_by: UUID | None = None
    verified_at: datetime | None = None
    released_by: UUID | None = None
    released_at: datetime | None = None
    amended_from_result_id: UUID | None = None
    amendment_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabCompletionResponse(BaseModel):
    lab_request_id: UUID
    visit_id: UUID
    status: LabRequestStatus
    completed_at: datetime
    visit_status: VisitStatus | None = None
    visit_ready_for_transition: bool
    suggested_next_visit_status: VisitStatus | None = None
    visit_transition_expected_version: int | None = None
