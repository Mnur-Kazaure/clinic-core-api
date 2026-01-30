# app/api/v1/admissions.py
from fastapi import APIRouter, Depends, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.core.guards.admission_guards import require_admission_role, require_admission_access
from app.schemas.admission import AdmissionCreateRequest, AdmissionCancelRequest, AdmissionResponse
from app.services.admission_service import AdmissionService


router = APIRouter(prefix="/admissions", tags=["admissions"])


@router.post(
    "",
    response_model=AdmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admission(
    payload: AdmissionCreateRequest,
    db=Depends(get_db),
    user=Depends(require_admission_role),
):
    service = AdmissionService(db)
    return service.create_admission(
        patient_id=payload.patient_id,
        admission_type=payload.admission_type,
        actor=user,
        break_glass=payload.break_glass,
        purpose_of_use=payload.purpose_of_use,
        reason=payload.reason,
    )


@router.get(
    "/{admission_id}",
    response_model=AdmissionResponse,
)
def get_admission(
    admission=Depends(require_admission_access),
):
    return admission


@router.post(
    "/{admission_id}/discharge",
    response_model=AdmissionResponse,
)
def discharge_admission(
    admission_id: UUID,
    db=Depends(get_db),
    user=Depends(require_admission_role),
):
    service = AdmissionService(db)
    return service.discharge_admission(admission_id=admission_id, actor=user)


@router.post(
    "/{admission_id}/cancel",
    response_model=AdmissionResponse,
)
def cancel_admission(
    admission_id: UUID,
    payload: AdmissionCancelRequest,
    db=Depends(get_db),
    user=Depends(require_admission_role),
):
    service = AdmissionService(db)
    return service.cancel_admission(
        admission_id=admission_id,
        actor=user,
        reason=payload.reason,
    )
