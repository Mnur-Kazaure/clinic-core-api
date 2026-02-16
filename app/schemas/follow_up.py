from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.enums import (
    DiagnosisMappingConfidence,
    DiagnosisSystem,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
    RecallIntervalUnit,
    RecallSuggestionConfidence,
    VisitServiceLine,
)


class ConditionProfileCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=200)
    recall_enabled: bool = True
    default_interval_value: int = Field(ge=1, le=3650)
    default_interval_unit: RecallIntervalUnit
    default_priority: FollowUpPriority = FollowUpPriority.IMPORTANT
    cooldown_days: int = Field(default=90, ge=0, le=3650)
    keyword_synonyms: list[str] = Field(default_factory=list)
    justification: str = Field(min_length=2, max_length=500)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("keyword_synonyms")
    @classmethod
    def normalize_synonyms(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            token = raw.strip()
            if not token:
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(token)
        return normalized


class ConditionProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=200)
    recall_enabled: bool | None = None
    default_interval_value: int | None = Field(default=None, ge=1, le=3650)
    default_interval_unit: RecallIntervalUnit | None = None
    default_priority: FollowUpPriority | None = None
    cooldown_days: int | None = Field(default=None, ge=0, le=3650)
    keyword_synonyms: list[str] | None = None
    justification: str = Field(min_length=2, max_length=500)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()

    @field_validator("keyword_synonyms")
    @classmethod
    def normalize_synonyms(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return values
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            token = raw.strip()
            if not token:
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(token)
        return normalized


class ConditionProfileResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    code: str
    display_name: str
    recall_enabled: bool
    default_interval_value: int
    default_interval_unit: RecallIntervalUnit
    default_priority: FollowUpPriority
    cooldown_days: int
    keyword_synonyms: list[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiagnosisConditionMapCreateRequest(BaseModel):
    diagnosis_system: DiagnosisSystem
    diagnosis_code: str = Field(min_length=1, max_length=64)
    condition_profile_id: UUID
    confidence: DiagnosisMappingConfidence = DiagnosisMappingConfidence.HIGH
    justification: str = Field(min_length=2, max_length=500)

    @field_validator("diagnosis_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

class DiagnosisConditionMapUpdateRequest(BaseModel):
    active: bool
    justification: str = Field(min_length=2, max_length=500)


class DiagnosisConditionMapResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    diagnosis_system: DiagnosisSystem
    diagnosis_code: str
    condition_profile_id: UUID
    confidence: DiagnosisMappingConfidence
    active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecallSuggestionItem(BaseModel):
    condition_profile_id: UUID
    condition_code: str
    display_name: str
    default_interval_value: int
    default_interval_unit: RecallIntervalUnit
    default_priority: FollowUpPriority
    confidence: RecallSuggestionConfidence


class ChronicRecallCreateRequest(BaseModel):
    patient_id: UUID
    condition_profile_id: UUID
    origin_visit_id: UUID | None = None
    interval_value_override: int | None = Field(default=None, ge=1, le=3650)
    interval_unit_override: RecallIntervalUnit | None = None
    justification: str = Field(min_length=2, max_length=500)


class ChronicRecallResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id_canonical: UUID
    condition_profile_id: UUID
    assigned_clinician_id: UUID
    interval_value: int
    interval_unit: RecallIntervalUnit
    next_due_at: datetime
    active: bool
    generation_paused: bool
    last_generated_due_at: datetime | None
    deactivated_at: datetime | None
    deactivated_reason: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowUpListItem(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id_canonical: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    type: FollowUpType
    priority: FollowUpPriority
    status: FollowUpStatus
    due_at: datetime
    reason: str
    owner_user_id: UUID
    owner_user_name: str | None = None
    owner_role: str
    recommended_service_line: VisitServiceLine
    active_visit_id: UUID | None = None
    linked_visit_id: UUID | None = None


class ClinicianFollowUpDashboardResponse(BaseModel):
    overdue: list[FollowUpListItem] = Field(default_factory=list)
    today: list[FollowUpListItem] = Field(default_factory=list)
    upcoming: list[FollowUpListItem] = Field(default_factory=list)


class ReceptionFollowUpDashboardResponse(BaseModel):
    today: list[FollowUpListItem] = Field(default_factory=list)
    tomorrow: list[FollowUpListItem] = Field(default_factory=list)


class FollowUpRescheduleRequest(BaseModel):
    due_at: datetime
    reason: str = Field(min_length=2, max_length=500)
    justification: str = Field(min_length=2, max_length=500)


class FollowUpRescheduleResponse(BaseModel):
    original_follow_up_id: UUID
    replacement: FollowUpListItem
