# app/api/v1/consultation.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from app.core.database import get_db
from app.core.auth.dependencies import get_current_user

# from app.core.dependencies import get_current_user
from app.core.rbac import require_doctor
from app.models.visit import Visit
from app.models.consultation import Consultation
from app.schemas.consultation import (
    ConsultationCreateRequest,
    ConsultationResponse,
    ConsultationUpdateRequest,
)
from app.services.consultation_service import ConsultationService
from app.services.access_log_service import AccessLogService
from app.shared.enums import VisitStatus, PurposeOfUse


from app.core.guards.consultation_guards import (
    ensure_assigned_doctor,
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
    response: Response,
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

    existing = (
        db.query(Consultation)
        .filter(Consultation.visit_id == visit.id)
        .first()
    )
    if existing:
        try:
            ensure_assigned_doctor(visit, current_user)
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        response.status_code = status.HTTP_200_OK
        return existing

    service = ConsultationService(db)

    try:
        consultation = service.start_consultation(visit, current_user)
        response.status_code = status.HTTP_201_CREATED
        return consultation

    except ValueError as e:
        if "already exists" in str(e):
            existing = (
                db.query(Consultation)
                .filter(Consultation.visit_id == visit.id)
                .first()
            )
            if existing:
                response.status_code = status.HTTP_200_OK
                return existing
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
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
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
            justification=justification,
            resource="CONSULTATION_DETAIL",
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=consultation.visit.patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="CONSULTATION_DETAIL",
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
