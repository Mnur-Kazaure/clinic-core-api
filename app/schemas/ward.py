# app/schemas/ward.py
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import WardType


class WardCreateRequest(BaseModel):
    name: str
    ward_type: WardType


class WardActiveUpdateRequest(BaseModel):
    active: bool
    reason: str | None = None


class WardResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    ward_type: WardType
    active: bool
    bed_label_prefix: str | None = None
    bed_label_padding: int | None = None
    bed_label_next: int | None = None

    model_config = ConfigDict(from_attributes=True)


class WardBedRangePreviewRequest(BaseModel):
    name: str = Field(..., min_length=2)
    ward_type: WardType
    label_prefix: str = Field(..., min_length=1)
    label_from: int = Field(..., ge=1)
    label_to: int = Field(..., ge=1)
    label_padding: int = Field(default=2, ge=0, le=6)


class WardBedRangePreviewResponse(BaseModel):
    name: str
    ward_type: WardType
    label_prefix: str
    label_from: int
    label_to: int
    label_padding: int
    total_beds: int
    bed_labels: list[str]
    conflicts: list[str] = []
    is_valid: bool = True


class WardBedRangeCreateRequest(WardBedRangePreviewRequest):
    pass


class WardBedRangeCreateResponse(BaseModel):
    ward: WardResponse
    created_beds: int
    bed_labels: list[str]


class WardAppendBedResponse(BaseModel):
    ward_id: UUID
    bed_id: UUID
    bed_label: str
    next_number: int | None = None


class WardRetireBedRequest(BaseModel):
    reason: str = Field(..., min_length=3)


class WardRetireBedResponse(BaseModel):
    ward_id: UUID
    bed_id: UUID
    bed_label: str
