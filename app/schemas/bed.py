# app/schemas/bed.py
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import BedStatus, WardType, AdmissionType
from app.schemas.admission import BedAssignmentTimelineItem


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


class BedStatusUpdateRequest(BaseModel):
    status: BedStatus
    reason: str | None = None


class BedActiveUpdateRequest(BaseModel):
    active: bool
    reason: str | None = None


BedBoardOccupancyStatus = Literal[
    "AVAILABLE",
    "OCCUPIED",
    "OUT_OF_SERVICE",
    "INACTIVE",
]


class BedBoardOccupant(BaseModel):
    admission_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    assigned_at: datetime


class BedBoardBed(BaseModel):
    bed_id: UUID
    bed_label: str
    bed_status: BedStatus
    bed_active: bool
    occupancy_status: BedBoardOccupancyStatus
    active_assignment_id: UUID | None = None
    occupant: BedBoardOccupant | None = None


class BedBoardWardSummary(BaseModel):
    ward_id: UUID
    ward_name: str
    ward_type: WardType
    ward_active: bool
    total_beds: int
    available_beds: int
    occupied_beds: int
    out_of_service_beds: int
    inactive_beds: int


class BedBoardWard(BaseModel):
    summary: BedBoardWardSummary
    beds: list[BedBoardBed]


class BedBoardTotals(BaseModel):
    total_beds: int
    available_beds: int
    occupied_beds: int
    out_of_service_beds: int
    inactive_beds: int


class BedBoardResponse(BaseModel):
    wards: list[BedBoardWard]
    totals: BedBoardTotals


class OccupiedBedItem(BaseModel):
    bed_id: UUID
    bed_label: str
    ward_id: UUID
    ward_name: str
    admission_id: UUID
    admission_type: AdmissionType
    patient_id: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    assigned_at: datetime
    review_due: bool = False
    chronic_due: bool = False


class OccupiedBedSearchResponse(BaseModel):
    total: int
    items: list[OccupiedBedItem]


class OccupiedBedDetailResponse(BaseModel):
    admission_id: UUID
    admission_type: AdmissionType
    patient_id: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    ward_name: str | None = None
    bed_label: str | None = None
    assigned_at: datetime | None = None
    review_due: bool = False
    chronic_due: bool = False
    timeline: list[BedAssignmentTimelineItem] = []
