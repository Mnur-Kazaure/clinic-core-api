# app/api/v1/bed_board.py
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db
from app.core.guards.bed_guards import require_bed_management_role
from uuid import UUID

from app.schemas.bed import (
    BedBoardResponse,
    OccupiedBedSearchResponse,
    OccupiedBedDetailResponse,
)
from app.services.bed_service import BedService


router = APIRouter(prefix="/bed-board", tags=["bed_board"])


@router.get(
    "",
    response_model=BedBoardResponse,
    status_code=status.HTTP_200_OK,
)
def get_bed_board(
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    service = BedService(db)
    return service.get_bed_board(clinic_id=user.clinic_id)


@router.get(
    "/occupied",
    response_model=OccupiedBedSearchResponse,
    status_code=status.HTTP_200_OK,
)
def list_occupied_beds(
    query: str | None = None,
    ward_id: UUID | None = None,
    limit: int = 25,
    offset: int = 0,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    service = BedService(db)
    return service.list_occupied_beds(
        clinic_id=user.clinic_id,
        query=query,
        ward_id=ward_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/occupied/{admission_id}",
    response_model=OccupiedBedDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_occupied_bed_detail(
    admission_id: UUID,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    service = BedService(db)
    return service.get_occupied_bed_detail(
        clinic_id=user.clinic_id,
        admission_id=admission_id,
    )
