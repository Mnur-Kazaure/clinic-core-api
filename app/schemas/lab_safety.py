from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.enums import (
    LabCriticalAlertSeverity,
    LabCriticalAlertStatus,
    LabCriticalAlertType,
    LabQcStatus,
    LabResultLifecycleStatus,
    LabVerificationPolicy,
)


class StructuredLabResultValueInput(BaseModel):
    template_field_id: UUID
    value_string: str | None = None
    value_number: float | None = None
    value_boolean: bool | None = None
    value_json: dict[str, Any] | list[Any] | None = None

    @model_validator(mode="after")
    def validate_at_least_one_value(self) -> "StructuredLabResultValueInput":
        if (
            self.value_string is None
            and self.value_number is None
            and self.value_boolean is None
            and self.value_json is None
        ):
            raise ValueError("At least one typed value is required")
        return self


class StructuredLabResultCreate(BaseModel):
    values: list[StructuredLabResultValueInput] = Field(min_length=1)


class LabResultValueResponse(BaseModel):
    id: UUID
    template_field_id: UUID
    value_string: str | None = None
    value_number: float | None = None
    value_boolean: bool | None = None
    value_json: dict[str, Any] | list[Any] | None = None
    abnormal_flag: bool
    critical_flag: bool

    model_config = ConfigDict(from_attributes=True)


class StructuredLabResultResponse(BaseModel):
    id: UUID
    request_item_id: UUID | None = None
    template_id: UUID | None = None
    template_version: int | None = None
    status: LabResultLifecycleStatus
    amendment_reason: str | None = None
    entered_by: UUID | None = None
    entered_at: datetime
    verified_by: UUID | None = None
    verified_at: datetime | None = None
    released_by: UUID | None = None
    released_at: datetime | None = None
    verification_policy: LabVerificationPolicy
    values: list[LabResultValueResponse]


class LabResultActionResponse(BaseModel):
    result_id: UUID
    status: LabResultLifecycleStatus
    verification_policy: LabVerificationPolicy
    critical_alert_count: int


class LabResultReleaseRequest(BaseModel):
    qc_override_reason: str | None = Field(default=None, min_length=4, max_length=255)


class LabResultAmendCreate(BaseModel):
    amendment_reason: str = Field(min_length=4, max_length=255)
    values: list[StructuredLabResultValueInput] = Field(min_length=1)


class LabCriticalAlertResponse(BaseModel):
    id: UUID
    result_id: UUID | None = None
    result_value_id: UUID | None = None
    request_item_id: UUID | None = None
    visit_id: UUID | None = None
    patient_id: UUID | None = None
    unit_id: UUID | None = None
    alert_type: LabCriticalAlertType
    severity: LabCriticalAlertSeverity
    message: str
    target_role: str
    target_user_id: UUID | None = None
    status: LabCriticalAlertStatus
    acknowledged_by: UUID | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    escalated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabQcRunCreate(BaseModel):
    unit_id: UUID
    machine_id: UUID | None = None
    qc_level: str = Field(min_length=1, max_length=64)
    notes: str | None = None


class LabQcRunResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    unit_id: UUID
    machine_id: UUID | None = None
    qc_level: str
    performed_by: UUID
    performed_at: datetime
    status: LabQcStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabQcResultCreate(BaseModel):
    analyte_name: str = Field(min_length=1, max_length=255)
    expected_min: float | None = None
    expected_max: float | None = None
    observed_value: float


class LabQcResultResponse(BaseModel):
    id: UUID
    qc_run_id: UUID
    analyte_name: str
    expected_min: float | None = None
    expected_max: float | None = None
    observed_value: float
    status: LabQcStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
