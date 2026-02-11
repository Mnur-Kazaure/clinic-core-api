# app/schemas/maternity.py
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.enums import (
    BabySex,
    DeliveryMode,
    DeliveryOutcome,
    FamilyPlanningCommodity,
    PostnatalSubject,
    RecordStatus,
)


class MaternityDeliveryUpsert(BaseModel):
    action: Literal["SAVE_DRAFT", "SIGN"] = "SAVE_DRAFT"
    episode_id: UUID | None = None
    delivered_at: datetime | None = None
    mode_of_delivery: DeliveryMode = DeliveryMode.UNKNOWN
    outcome: DeliveryOutcome = DeliveryOutcome.UNKNOWN
    baby_sex: BabySex = BabySex.UNKNOWN
    baby_weight_kg: float | None = None
    apgar_1: int | None = None
    apgar_5: int | None = None
    maternal_complications: str | None = None
    newborn_complications: str | None = None
    notes: str | None = None


class MaternityDeliveryResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    visit_id: UUID
    episode_id: UUID | None
    recorded_by: UUID
    recorded_at: datetime
    record_status: RecordStatus
    signed_at: datetime | None
    void_reason: str | None
    delivered_at: datetime | None
    mode_of_delivery: DeliveryMode
    outcome: DeliveryOutcome
    baby_sex: BabySex
    baby_weight_kg: float | None
    apgar_1: int | None
    apgar_5: int | None
    maternal_complications: str | None
    newborn_complications: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class PostnatalNoteCreate(BaseModel):
    subject: PostnatalSubject
    note: str


class PostnatalNoteResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    visit_id: UUID
    subject: PostnatalSubject
    note: str
    added_by: UUID
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FamilyPlanningEventCreate(BaseModel):
    commodity: FamilyPlanningCommodity
    notes: str | None = None


class FamilyPlanningEventResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    visit_id: UUID
    commodity: FamilyPlanningCommodity
    notes: str | None
    added_by: UUID
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)
