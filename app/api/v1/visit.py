# app/api/v1/visit.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID


from app.core.idempotency import idempotent, hash_request
from app.models.idempotency import IdempotencyKey

from app.core.idempotency import idempotent
from app.core.rbac import require_visit_access
from app.schemas.visit import (
    VisitResponse,
    VisitTransitionRequest,
)
from app.services.visit.service import VisitService
from app.services.access_log_service import AccessLogService
from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.shared.enums import VisitStatus

from app.models.visit import Visit
from app.models.patient import Patient
from app.schemas.visit import AllowedTransitionsResponse
from app.schemas.visit import VisitTimelineResponse


router = APIRouter(prefix="/visits", tags=["Visits"])



from app.schemas.visit import VisitCreateRequest, VisitCreateResponse

from datetime import datetime
from app.core.rbac import require_reception
from app.core.rbac import require_doctor
import uuid

from datetime import date, datetime, timezone
from typing import Optional, List
from app.schemas.visit import VisitResponse
from app.core.rbac import require_reception




@router.post(
    "/start",
    response_model=VisitCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_visit(
    payload: VisitCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    """
    START VISIT — This endpoint represents the moment clinical care begins.

    Semantics:
    - Initiated ONLY by Reception
    - Creates a Visit
    - Assigns doctor
    - Sets started_at (legal timestamp)
    - Patient enters clinical workflow
    """

    service = VisitService(db)
    visit = service.start_visit(payload, current_user)
    _attach_patient_name(db, visit)
    return visit


# Transition a visit to a new status
@router.post(
    "/{visit_id}/transition",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def transition_visit(
    visit_id: UUID,
    payload: VisitTransitionRequest,
    dep=Depends(idempotent("VISIT_TRANSITION")),
    current_user=Depends(require_visit_access),
):
    record, key, db = dep

    # 🔁 Replay short-circuit
    if record:
        return record.response_body

    service = VisitService(db)

    try:
        visit = service.transition_visit(
            visit_id=visit_id,
            to_status=payload.to_status,
            user=current_user,
        )

        # 🔒 Clinic boundary
        if visit.clinic_id != current_user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )

        # ✅ JSON-safe serialization (FIX)
        _attach_patient_name(db, visit)
        response_payload = VisitResponse.model_validate(
            visit,
            from_attributes=True,
        ).model_dump(mode="json")

        # ✅ Persist idempotency atomically
        db.add(
            IdempotencyKey(
                id=uuid.uuid4(),
                key=key,
                user_id=current_user.id,
                endpoint="VISIT_TRANSITION",
                request_hash=hash_request(payload.dict()),
                response_body=response_payload,
            )
        )
        db.commit()

        # ✅ ALWAYS return serialized payload
        return response_payload

    except PermissionError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )




# Get allowed transitions for a visit
@router.get(
    "/{visit_id}/allowed-transitions",
    response_model=AllowedTransitionsResponse,
)
def get_allowed_transitions(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )
    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    service = VisitService(db)
    allowed = service.get_allowed_transitions(visit, current_user)

    return {"allowed": allowed}


# Get visit timeline
@router.get(
    "/{visit_id}/timeline",
    response_model=VisitTimelineResponse,
)
def get_visit_timeline(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    service = VisitService(db)
    timeline = service.get_visit_timeline(visit_id)

    return {
        "visit_id": visit_id,
        "timeline": timeline,
    }


# Get reception queue
@router.get("/queue", response_model=list[VisitResponse])
def get_queue(
    status: Optional[VisitStatus] = None,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    """
    Reception queue for current clinic.
    Optional filter by status.
    MVP: returns all visits for clinic (optionally by status).
    """
    service = VisitService(db)
    visits = service.get_queue_for_clinic(
        clinic_id=current_user.clinic_id,
        status=status,
    )
    _attach_patient_names(db, visits)
    return visits

# app/api/v1/visit.py
# Doctor visit queue
@router.get("/doctor-queue", response_model=list[VisitResponse])
def get_doctor_queue(
    status: Optional[VisitStatus] = None,
    db=Depends(get_db),
    current_user=Depends(require_doctor),
):
    """
    Doctor queue for current clinic.
    Optional filter by status.
    Returns visits assigned to current doctor only.
    """
    service = VisitService(db)
    visits = service.get_queue_for_doctor(
        clinic_id=current_user.clinic_id,
        doctor_id=current_user.id,
        status=status,
    )
    _attach_patient_names(db, visits)
    return visits


@router.get("/recent", response_model=list[VisitResponse])
def get_recent_visits(
    limit: int = 10,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    visits = (
        db.query(Visit)
        .filter(Visit.clinic_id == current_user.clinic_id)
        .order_by(Visit.updated_at.desc())
        .limit(limit)
        .all()
    )
    _attach_patient_names(db, visits)
    return visits


# Get visit details
@router.get(
    "/{visit_id}",
    response_model=VisitResponse,
)
def get_visit(
    visit_id: UUID,
    purpose_of_use: str = Query(..., min_length=2),
    reason: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    if break_glass:
        AccessLogService(db).log_break_glass(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            reason=reason,
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            reason=reason,
        )
    _attach_patient_name(db, visit)
    return visit
def _attach_patient_name(db, visit: Visit) -> None:
    patient = (
        db.query(Patient)
        .filter(Patient.id == visit.patient_id)
        .first()
    )
    visit.patient_name = patient.full_name if patient else None


def _attach_patient_names(db, visits: list[Visit]) -> None:
    if not visits:
        return
    patient_ids = {visit.patient_id for visit in visits}
    patients = (
        db.query(Patient)
        .filter(Patient.id.in_(patient_ids))
        .all()
    )
    patient_map = {patient.id: patient.full_name for patient in patients}
    for visit in visits:
        visit.patient_name = patient_map.get(visit.patient_id)
