# app/api/v1/consultation.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.database import get_db
from app.core.auth.dependencies import get_current_user

# from app.core.dependencies import get_current_user
from app.core.rbac import require_doctor
from app.models.visit import Visit
from app.schemas.consultation import (
    ConsultationCreateRequest,
    ConsultationResponse,
    ConsultationUpdateRequest,
)
from app.services.consultation_service import ConsultationService
from app.services.access_log_service import AccessLogService
from app.shared.enums import VisitStatus


from app.core.guards.consultation_guards import (
    require_consultation_access,
    require_consultation_access_by_visit,
)

router = APIRouter(prefix="/consultations", tags=["Consultations"])

# Start a new consultation
@router.post(
    "/start",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_consultation(
    payload: ConsultationCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_doctor),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == payload.visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if visit.status != VisitStatus.IN_CONSULTATION:
        raise HTTPException(
            status_code=400,
            detail="Visit not ready for consultation",
        )

    service = ConsultationService(db)

    try:
        return service.start_consultation(visit, current_user)

    except ValueError as e:
        # Domain rule violation → client error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/visit/{visit_id}",
    response_model=ConsultationResponse,
)
def get_consultation_by_visit(
    purpose_of_use: str = Query(..., min_length=2),
    reason: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    consultation=Depends(require_consultation_access_by_visit),
):
    if break_glass:
        AccessLogService(db).log_break_glass(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=consultation.visit.patient_id,
            purpose_of_use=purpose_of_use,
            reason=reason,
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=consultation.visit.patient_id,
            purpose_of_use=purpose_of_use,
            reason=reason,
        )
    return consultation

# Update an existing consultation
@router.patch(
    "/{consultation_id}",
    response_model=ConsultationResponse,
)
def update_consultation(
    consultation_id: UUID,
    payload: ConsultationUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    consultation=Depends(require_consultation_access),
):
    service = ConsultationService(db)

    return service.update_consultation(
        consultation,
        current_user,
        vitals=payload.vitals,
        presenting_complaints=payload.presenting_complaints,
        diagnosis=payload.diagnosis,
        notes=payload.notes,
        doctor_full_name=payload.doctor_full_name,
    )


@router.post(
    "/{consultation_id}/complete",
    response_model=ConsultationResponse,
)
def complete_consultation(
    consultation_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    consultation=Depends(require_consultation_access),
):
    service = ConsultationService(db)

    return service.complete_consultation(
        consultation,
        current_user,
    )
