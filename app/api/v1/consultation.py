# app/api/v1/consultation.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
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
from app.shared.enums import VisitStatus
from app.models.consultation import Consultation


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
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ConsultationService(db)
    consultation = service.get_by_visit(visit_id)

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

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
    current_user=Depends(require_doctor),
):
    consultation = (
        db.query(Consultation)
        .filter(Consultation.id == consultation_id)
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Consultation not found",
        )

    service = ConsultationService(db)

    return service.update_consultation(
        consultation,
        current_user,
        vitals=payload.vitals,
        presenting_complaints=payload.presenting_complaints,
        diagnosis=payload.diagnosis,
        notes=payload.notes,
    )


@router.post(
    "/{consultation_id}/complete",
    response_model=ConsultationResponse,
)
def complete_consultation(
    consultation_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_doctor),
):
    consultation = (
        db.query(Consultation)
        .filter(Consultation.id == consultation_id)
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Consultation not found",
        )

    service = ConsultationService(db)

    return service.complete_consultation(
        consultation,
        current_user,
    )