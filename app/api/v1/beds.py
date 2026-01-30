# app/api/v1/beds.py
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db
from app.core.guards.bed_guards import require_bed_management_role
from app.models.bed import Bed
from app.schemas.bed import BedCreateRequest, BedResponse, BedAssignRequest, BedTransferRequest
from app.services.bed_service import BedService


router = APIRouter(prefix="/beds", tags=["beds"])


@router.post(
    "",
    response_model=BedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bed(
    payload: BedCreateRequest,
    db=Depends(get_db),
    user=Depends(require_bed_management_role),
):
    bed = Bed(
        clinic_id=user.clinic_id,
        ward_id=payload.ward_id,
        bed_label=payload.bed_label,
        status=payload.status,
        active=True,
    )
    db.add(bed)
    db.commit()
    db.refresh(bed)
    return bed


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
        break_glass_reason=payload.break_glass_reason,
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
        break_glass_reason=payload.break_glass_reason,
    )
