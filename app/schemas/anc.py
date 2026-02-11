# app/schemas/anc.py
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.enums import PregnancyEpisodeStatus, RecordStatus


class PregnancyEpisodeCreate(BaseModel):
    lmp_date: date | None = None
    edd_date: date | None = None
    gravida: int | None = None
    parity: int | None = None
    booking_reg_no: str | None = None
    past_medical_history: str | None = None
    past_surgical_history: str | None = None
    history_present_pregnancy: str | None = None
    general_exam: str | None = None
    close_existing: bool = False


class PregnancyEpisodeResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    status: PregnancyEpisodeStatus
    lmp_date: date | None
    edd_date: date | None
    gravida: int | None
    parity: int | None
    booking_reg_no: str | None
    past_medical_history: str | None
    past_surgical_history: str | None
    history_present_pregnancy: str | None
    general_exam: str | None
    created_by: UUID
    created_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PreviousPregnancyCreate(BaseModel):
    year: int | None = None
    duration: str | None = None
    antenatal_complications: str | None = None
    labour: str | None = None
    age_alive: str | None = None
    age_dead: str | None = None
    cause_of_death: str | None = None


class PreviousPregnancyResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    episode_id: UUID
    year: int | None
    duration: str | None
    antenatal_complications: str | None
    labour: str | None
    age_alive: str | None
    age_dead: str | None
    cause_of_death: str | None
    created_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ANCEncounterUpsert(BaseModel):
    action: Literal["SAVE_DRAFT", "SIGN"] = "SAVE_DRAFT"
    episode_id: UUID
    fundus_height: str | None = None
    presentation_position: str | None = None
    presenting_part: str | None = None
    foetal_heart: str | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    urine: str | None = None
    weight_kg: float | None = None
    remarks: str | None = None
    ref: str | None = None
    initial: str | None = None


class ANCEncounterResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    visit_id: UUID
    episode_id: UUID
    recorded_by: UUID
    recorded_at: datetime
    record_status: RecordStatus
    signed_at: datetime | None
    void_reason: str | None
    fundus_height: str | None
    presentation_position: str | None
    presenting_part: str | None
    foetal_heart: str | None
    bp_systolic: int | None
    bp_diastolic: int | None
    urine: str | None
    weight_kg: float | None
    remarks: str | None
    ref: str | None
    initial: str | None

    model_config = ConfigDict(from_attributes=True)
