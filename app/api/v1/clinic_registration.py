# app/api/v1/clinic_registration.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.clinic import ClinicRegistrationRequest
from app.services.clinic_service.service import ClinicService


router = APIRouter(prefix="/clinic", tags=["Clinic"])


@router.post(
    "/register-clinic",
    status_code=status.HTTP_201_CREATED,
)
def register_clinic(
    payload: ClinicRegistrationRequest,
    db: Session = Depends(get_db),
):
    clinic, admin = ClinicService(db).register_clinic(payload)

    return {
        "clinic_id": str(clinic.id),
        "admin_user_id": str(admin.id),
        "message": "Clinic registered successfully",
    }
