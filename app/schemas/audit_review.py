# app/schemas/audit_review.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import AuditCaseSeverity, AuditCaseStatus, AuditCaseOutcome, AuditItemType


class AuditReviewCaseCreateRequest(BaseModel):
    severity: AuditCaseSeverity
    reason: str = Field(min_length=3)


class AuditReviewCaseStartRequest(BaseModel):
    reason: str = Field(min_length=3)


class AuditReviewCaseCloseRequest(BaseModel):
    outcome: AuditCaseOutcome
    reason: str = Field(min_length=3)


class AuditReviewItemCreateRequest(BaseModel):
    item_type: AuditItemType
    access_log_id: UUID | None = None
    event_log_id: UUID | None = None
    notes: str | None = None


class AuditReviewCaseResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    status: AuditCaseStatus
    severity: AuditCaseSeverity
    reason: str
    created_by: UUID
    created_at: datetime
    reviewed_by: UUID | None
    closed_by: UUID | None
    closed_at: datetime | None
    outcome: AuditCaseOutcome | None

    model_config = ConfigDict(from_attributes=True)


class AuditReviewItemResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    case_id: UUID
    item_type: AuditItemType
    access_log_id: UUID | None
    event_log_id: UUID | None
    added_by: UUID
    added_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
