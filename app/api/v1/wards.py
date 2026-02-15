# app/api/v1/wards.py
from fastapi import APIRouter, Depends, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.guards.bed_guards import require_bed_management_role
from app.schemas.ward import (
    WardCreateRequest,
    WardResponse,
    WardActiveUpdateRequest,
    WardBedRangePreviewRequest,
    WardBedRangePreviewResponse,
    WardBedRangeCreateRequest,
    WardBedRangeCreateResponse,
    WardAppendBedResponse,
    WardRetireBedRequest,
    WardRetireBedResponse,
)


router = APIRouter(prefix="/wards", tags=["wards"])

@router.get(
    "",
    response_model=list[WardResponse],
    status_code=status.HTTP_200_OK,
)
def list_wards(
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    from app.services.bed_service import BedService

    service = BedService(db)
    return service.list_wards(clinic_id=user.clinic_id)


@router.post(
    "",
    response_model=WardResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ward(
    payload: WardCreateRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    from app.services.bed_service import BedService

    service = BedService(db)
    return service.create_ward(
        clinic_id=user.clinic_id,
        name=payload.name,
        ward_type=payload.ward_type,
    )


@router.post(
    "/range/preview",
    response_model=WardBedRangePreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_ward_bed_range(
    payload: WardBedRangePreviewRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    from app.services.bed_service import BedService

    service = BedService(db)
    return service.preview_ward_bed_range(clinic_id=user.clinic_id, payload=payload)


@router.post(
    "/range",
    response_model=WardBedRangeCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ward_with_bed_range(
    payload: WardBedRangeCreateRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    from app.services.bed_service import BedService

    service = BedService(db)
    return service.create_ward_with_bed_range(
        clinic_id=user.clinic_id, payload=payload
    )


@router.post(
    "/{ward_id}/active",
    response_model=WardResponse,
    status_code=status.HTTP_200_OK,
)
def set_ward_active(
    ward_id: UUID,
    payload: WardActiveUpdateRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    from app.services.bed_service import BedService

    service = BedService(db)
    return service.set_ward_active(
        clinic_id=user.clinic_id,
        ward_id=ward_id,
        active=payload.active,
        actor=user,
        reason=payload.reason,
    )


@router.post(
    "/{ward_id}/beds/append",
    response_model=WardAppendBedResponse,
    status_code=status.HTTP_201_CREATED,
)
def append_ward_bed(
    ward_id: UUID,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    from app.services.bed_service import BedService

    service = BedService(db)
    return service.append_next_bed(clinic_id=user.clinic_id, ward_id=ward_id, actor=user)


@router.post(
    "/{ward_id}/beds/retire-last",
    response_model=WardRetireBedResponse,
    status_code=status.HTTP_200_OK,
)
def retire_last_ward_bed(
    ward_id: UUID,
    payload: WardRetireBedRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    from app.services.bed_service import BedService

    service = BedService(db)
    return service.retire_last_bed(
        clinic_id=user.clinic_id,
        ward_id=ward_id,
        actor=user,
        reason=payload.reason,
    )
