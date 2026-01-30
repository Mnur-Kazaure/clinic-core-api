# app/api/v1/wards.py
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.core.guards.bed_guards import require_bed_management_role
from app.models.ward import Ward
from app.schemas.ward import WardCreateRequest, WardResponse


router = APIRouter(prefix="/wards", tags=["wards"])


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
    ward = Ward(
        clinic_id=user.clinic_id,
        name=payload.name,
        ward_type=payload.ward_type,
        active=True,
    )
    db.add(ward)
    db.commit()
    db.refresh(ward)
    return ward
