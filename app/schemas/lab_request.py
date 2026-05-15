# app/schemas/lab_request.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from app.shared.enums import (
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
)


class LabRequestCreate(BaseModel):
    visit_id: UUID
    test_name: str
    test_code: str | None = None
    special_instructions: str | None = None


class LabRequestResponse(BaseModel):
    id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    test_name: str
    test_code: str | None = None
    special_instructions: str | None = None
    status: LabRequestStatus
    requested_by: UUID
    requested_by_name: str | None = None
    requested_by_role: str | None = None
    billing_item_id: UUID | None = None
    billing_status: str | None = None
    billing_total_minor: int | None = None
    billing_currency: str | None = None
    payment_verified: bool | None = None
    workflow_status: LabRequestWorkflowStatus | None = None
    target_unit_id: UUID | None = None
    target_unit_name: str | None = None
    ready_specimen_count: int = 0
    critical_alert_count: int = 0
    active_result_id: UUID | None = None
    latest_result_status: LabResultLifecycleStatus | None = None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
