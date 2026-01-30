# app/api/v1/clinic_staff.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.rbac import require_clinic_admin
from app.core.database import get_db
from app.schemas.clinic import StaffCreateRequest, StaffUpdateRequest, StaffResponse
from app.services.clinic_service.service import ClinicService


router = APIRouter(prefix="/clinic", tags=["Clinic"])


@router.post(
    "/staff",
    status_code=status.HTTP_201_CREATED,
)
def create_staff(
    payload: StaffCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    """
    Provision a staff user under the same clinic.
    Accessible only by Clinic Admin.
    """
    service = ClinicService(db)
    user = service.create_staff_user(
        payload=payload,
        current_user=current_user,
    )

    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "message": "Staff user created successfully",
    }


@router.get(
    "/staff",
    response_model=list[StaffResponse],
    status_code=status.HTTP_200_OK,
)
def list_staff(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ClinicService(db)
    return service.list_staff(current_user.clinic_id)


@router.patch(
    "/staff/{staff_id}",
    response_model=StaffResponse,
    status_code=status.HTTP_200_OK,
)
def update_staff(
    staff_id: UUID,
    payload: StaffUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ClinicService(db)
    return service.update_staff_user(
        staff_id=staff_id,
        payload=payload,
        current_user=current_user,
    )


@router.delete(
    "/staff/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = ClinicService(db)
    service.delete_staff_user(
        staff_id=staff_id,
        current_user=current_user,
    )
