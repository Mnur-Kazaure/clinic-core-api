# app/api/v1/clinic_profile.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_clinic_admin
from app.core.auth import get_current_user
from app.shared.enums import UserRole
from app.schemas.clinic import (
    ClinicProfileResponse,
    ClinicProfileUpdateRequest,
    ClinicRegistrationFeeResponse,
)
from app.services.clinic_service.service import ClinicService


router = APIRouter(prefix="/clinic", tags=["Clinic"])


@router.get(
    "/profile",
    response_model=ClinicProfileResponse,
    status_code=status.HTTP_200_OK,
)
def get_clinic_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ClinicService(db)
    return service.get_clinic_profile(current_user.clinic_id)


@router.patch(
    "/profile",
    response_model=ClinicProfileResponse,
    status_code=status.HTTP_200_OK,
)
def update_clinic_profile(
    payload: ClinicProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ClinicService(db)
    return service.update_clinic_profile(
        clinic_id=current_user.clinic_id,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/registration-fee",
    response_model=ClinicRegistrationFeeResponse,
    status_code=status.HTTP_200_OK,
)
def get_registration_fee(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in {UserRole.RECEPTION, UserRole.CLINIC_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    clinic = ClinicService(db).get_clinic_profile(current_user.clinic_id)
    return ClinicRegistrationFeeResponse(
        registration_fee_minor=clinic.registration_fee_minor,
        registration_fee_required=clinic.registration_fee_required,
        billing_currency=clinic.billing_currency,
    )
