from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.shared.enums import (
    LabCriticalAlertSeverity,
    LabCriticalAlertStatus,
    LabCriticalAlertType,
    LabResultFieldType,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
)


class DoctorLabVisitResultSummaryResponse(BaseModel):
    result_id: UUID
    lab_request_id: UUID
    request_item_id: UUID | None = None
    test_name: str
    test_code: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    requested_at: datetime
    released_at: datetime
    status: LabResultLifecycleStatus
    has_abnormal: bool
    has_critical: bool
    is_amended: bool
    is_superseded: bool
    critical_alert_count: int
    accession_numbers: list[str]
    specimen_count: int


class DoctorLabResultFieldValueResponse(BaseModel):
    template_field_id: UUID | None = None
    field_code: str
    field_name: str
    field_type: LabResultFieldType
    unit: str | None = None
    reference_range_text: str | None = None
    reference_min: float | None = None
    reference_max: float | None = None
    reference_unit: str | None = None
    options_json: list[str] | dict[str, Any] | None = None
    value_string: str | None = None
    value_number: float | None = None
    value_boolean: bool | None = None
    value_json: dict[str, Any] | list[Any] | None = None
    abnormal_flag: bool
    critical_flag: bool


class DoctorLabSpecimenContextResponse(BaseModel):
    specimen_id: UUID
    accession_number: str
    specimen_type: str
    specimen_source: str
    container_type: str | None = None
    collection_site: str | None = None
    specimen_sequence: int
    specimen_label_suffix: str | None = None
    status: LabSpecimenStatus
    collected_at: datetime | None = None
    received_at: datetime | None = None


class DoctorLabResultAlertResponse(BaseModel):
    alert_id: UUID
    alert_type: LabCriticalAlertType
    severity: LabCriticalAlertSeverity
    status: LabCriticalAlertStatus
    message: str
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    escalated_at: datetime | None = None


class DoctorLabResultVersionResponse(BaseModel):
    result_id: UUID
    released_at: datetime | None = None
    entered_at: datetime
    status: LabResultLifecycleStatus
    is_amended: bool
    is_superseded: bool
    amendment_reason: str | None = None


class DoctorLabResultAttachmentResponse(BaseModel):
    attachment_type: str
    uploaded_by: UUID
    uploaded_at: datetime
    source: str
    file_name: str
    file_url: str


class DoctorLabResultDetailResponse(BaseModel):
    result_id: UUID
    visit_id: UUID
    patient_id: UUID
    patient_name: str
    patient_mrn: str | None = None
    test_name: str
    test_code: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    requested_at: datetime
    status: LabResultLifecycleStatus
    released_at: datetime | None = None
    entered_at: datetime
    verified_at: datetime | None = None
    entered_by: UUID | None = None
    entered_by_name: str | None = None
    verified_by: UUID | None = None
    verified_by_name: str | None = None
    released_by: UUID | None = None
    released_by_name: str | None = None
    accession_numbers: list[str]
    has_abnormal: bool
    has_critical: bool
    is_amended: bool
    is_superseded: bool
    state_labels: list[str]
    amendment_reason: str | None = None
    values: list[DoctorLabResultFieldValueResponse]
    specimens: list[DoctorLabSpecimenContextResponse]
    alerts: list[DoctorLabResultAlertResponse]
    prior_versions: list[DoctorLabResultVersionResponse]
    attachments: list[DoctorLabResultAttachmentResponse] = []


class DoctorPatientLabHistoryEntryResponse(BaseModel):
    result_id: UUID
    visit_id: UUID
    released_at: datetime
    test_name: str
    test_code: str | None = None
    has_abnormal: bool
    has_critical: bool
    is_amended: bool
    accession_numbers: list[str]
    values: list[DoctorLabResultFieldValueResponse]
