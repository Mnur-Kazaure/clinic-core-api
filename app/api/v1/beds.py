# app/api/v1/beds.py
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db
from app.core.guards.bed_guards import (
    require_bed_capacity_admin,
    require_bed_management_role,
)
from app.schemas.bed import (
    BedCreateRequest,
    BedResponse,
    BedAssignRequest,
    BedTransferRequest,
    BedStatusUpdateRequest,
    BedActiveUpdateRequest,
)
from app.services.bed_service import BedService


router = APIRouter(prefix="/beds", tags=["beds"])

@router.get(
    "",
    response_model=list[BedResponse],
    status_code=status.HTTP_200_OK,
)
def list_beds(
    available_only: bool = False,
    ward_id: UUID | None = None,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    service = BedService(db)
    return service.list_beds(
        clinic_id=user.clinic_id,
        available_only=available_only,
        ward_id=ward_id,
    )


@router.post(
    "",
    response_model=BedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bed(
    payload: BedCreateRequest,
    db=Depends(get_db),
    user=Depends(require_bed_capacity_admin),
):
    service = BedService(db)
    return service.create_bed(
        clinic_id=user.clinic_id,
        ward_id=payload.ward_id,
        bed_label=payload.bed_label,
        status_value=payload.status,
    )


@router.post(
    "/assign",
    status_code=status.HTTP_201_CREATED,
)
def assign_bed(
    payload: BedAssignRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    service = BedService(db)
    return service.assign_bed(
        admission_id=payload.admission_id,
        bed_id=payload.bed_id,
        actor=user,
        reason=payload.reason,
        break_glass=payload.break_glass,
        purpose_of_use=payload.purpose_of_use,
    )


@router.post(
    "/transfer",
    status_code=status.HTTP_201_CREATED,
)
def transfer_bed(
    payload: BedTransferRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    service = BedService(db)
    return service.transfer_bed(
        admission_id=payload.admission_id,
        to_bed_id=payload.to_bed_id,
        actor=user,
        reason=payload.reason,
        break_glass=payload.break_glass,
        purpose_of_use=payload.purpose_of_use,
    )


@router.post(
    "/{bed_id}/status",
    response_model=BedResponse,
    status_code=status.HTTP_200_OK,
)
def update_bed_status(
    bed_id: UUID,
    payload: BedStatusUpdateRequest,
    db=Depends(get_db),
    user=Depends(require_bed_capacity_admin),
):
    service = BedService(db)
    return service.update_bed_status(
        clinic_id=user.clinic_id,
        bed_id=bed_id,
        status_value=payload.status,
        actor=user,
        reason=payload.reason,
    )


@router.post(
    "/{bed_id}/active",
    response_model=BedResponse,
    status_code=status.HTTP_200_OK,
)
def set_bed_active(
    bed_id: UUID,
    payload: BedActiveUpdateRequest,
    db=Depends(get_db),
    user=Depends(require_bed_capacity_admin),
):
    service = BedService(db)
    return service.set_bed_active(
        clinic_id=user.clinic_id,
        bed_id=bed_id,
        active=payload.active,
        actor=user,
        reason=payload.reason,
    )
