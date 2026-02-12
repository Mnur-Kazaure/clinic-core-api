# app/schemas/bed.py
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import BedStatus


class BedCreateRequest(BaseModel):
    ward_id: UUID
    bed_label: str
    status: BedStatus = BedStatus.AVAILABLE


class BedResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    ward_id: UUID
    bed_label: str
    status: BedStatus
    active: bool

    model_config = ConfigDict(from_attributes=True)


class BedAssignRequest(BaseModel):
    admission_id: UUID
    bed_id: UUID
    reason: str | None = None
    break_glass: bool = False
    purpose_of_use: str | None = None


class BedTransferRequest(BaseModel):
    admission_id: UUID
    to_bed_id: UUID
    reason: str = Field(..., min_length=3)
    break_glass: bool = False
    purpose_of_use: str | None = None
