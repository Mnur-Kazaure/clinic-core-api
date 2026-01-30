# app/schemas/ward.py
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.shared.enums import WardType


class WardCreateRequest(BaseModel):
    name: str
    ward_type: WardType


class WardResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    ward_type: WardType
    active: bool

    model_config = ConfigDict(from_attributes=True)
