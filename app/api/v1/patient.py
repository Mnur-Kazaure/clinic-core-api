from fastapi import APIRouter, Depends, status

from app.schemas.patient import PatientCreateSchema, PatientReadSchema
from app.services.patient_service import PatientService
from app.core.dependencies import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/patient", tags=["Patient"])


@router.post(
    "",
    response_model=PatientReadSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    payload: PatientCreateSchema,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = PatientService(db)
    return service.create_patient(payload, current_user)