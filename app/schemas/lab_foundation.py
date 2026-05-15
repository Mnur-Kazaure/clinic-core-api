from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    LabResultFieldType,
    LabResultTemplateType,
    LabSpecimenEventType,
    LabSpecimenRejectionReasonCode,
    LabSpecimenStatus,
)


class LabResultTemplateFieldResponse(BaseModel):
    id: UUID
    field_code: str
    field_name: str
    field_type: LabResultFieldType
    display_order: int
    is_required: bool
    unit: str | None = None
    reference_range_text: str | None = None
    reference_min: float | None = None
    reference_max: float | None = None
    reference_unit: str | None = None
    options_json: list[str] | dict[str, Any] | None = None
    validation_rules_json: dict[str, Any] | list[Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class LabResultTemplateResponse(BaseModel):
    id: UUID
    code: str
    name: str
    result_type: LabResultTemplateType
    version: int
    description: str | None = None
    is_active: bool
    fields: list[LabResultTemplateFieldResponse]


class LabSpecimenCreate(BaseModel):
    target_unit_id: UUID | None = None
    specimen_type: str = Field(min_length=1, max_length=80)
    specimen_source: str = Field(min_length=1, max_length=80)
    container_type: str | None = Field(default=None, max_length=80)
    collection_site: str | None = Field(default=None, max_length=80)
    specimen_sequence: int = Field(default=1, ge=1)
    specimen_label_suffix: str | None = Field(default=None, max_length=16)
    status: LabSpecimenStatus = LabSpecimenStatus.PENDING_COLLECTION
    collected_at: datetime | None = None
    received_at: datetime | None = None
    print_label: bool = False


class LabSpecimenResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    accession_number: str
    request_item_id: UUID
    target_unit_id: UUID
    specimen_type: str
    specimen_source: str
    container_type: str | None = None
    collection_site: str | None = None
    specimen_sequence: int
    specimen_label_suffix: str | None = None
    collected_by: UUID | None = None
    collected_at: datetime | None = None
    received_by: UUID | None = None
    received_at: datetime | None = None
    status: LabSpecimenStatus
    rejection_reason_code: LabSpecimenRejectionReasonCode | None = None
    rejection_reason_text: str | None = None
    rejected_by: UUID | None = None
    rejected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabSpecimenEventCreate(BaseModel):
    event_type: LabSpecimenEventType
    notes: str | None = None
    metadata_json: dict[str, Any] | list[Any] | None = None
    rejection_reason_code: LabSpecimenRejectionReasonCode | None = None
    rejection_reason_text: str | None = None
    target_unit_id: UUID | None = None
    performed_at: datetime | None = None


class LabSpecimenEventResponse(BaseModel):
    id: UUID
    specimen_id: UUID
    event_type: LabSpecimenEventType
    performed_by: UUID | None = None
    performed_at: datetime
    notes: str | None = None
    metadata_json: dict[str, Any] | list[Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
