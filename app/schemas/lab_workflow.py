from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.shared.enums import LabVerificationPolicy


class LabWorkflowStatusChipResponse(BaseModel):
    key: str
    label: str
    value: str
    tone: str


class LabWorkflowChecklistItemResponse(BaseModel):
    key: str
    label: str
    state: str
    detail: str | None = None


class LabSpecimenDefaultsResponse(BaseModel):
    specimen_type: str | None = None
    specimen_source: str | None = None
    container_type: str | None = None
    collection_site: str | None = None


class LabRequestWorkflowStateResponse(BaseModel):
    request_id: UUID
    request_status: str
    workflow_status: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    verification_policy: LabVerificationPolicy
    completion_message: str
    can_complete: bool
    status_chips: list[LabWorkflowStatusChipResponse]
    checklist: list[LabWorkflowChecklistItemResponse]
    specimen_defaults: LabSpecimenDefaultsResponse
