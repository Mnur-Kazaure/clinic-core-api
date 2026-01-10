# app/api/v1/visit.py
from fastapi import APIRouter, Depends, HTTPException, status
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
from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.shared.enums import VisitStatus

from app.models.visit import Visit
from app.schemas.visit import AllowedTransitionsResponse
from app.schemas.visit import VisitTimelineResponse


router = APIRouter(prefix="/visits", tags=["Visits"])



from app.schemas.visit import VisitCreateRequest, VisitCreateResponse

from datetime import datetime
from app.core.rbac import require_reception
import uuid


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

    # 🔒 Prevent multiple active visits for same patient
    existing = (
        db.query(Visit)
        .filter(
            Visit.patient_id == payload.patient_id,
            Visit.clinic_id == current_user.clinic_id,
            Visit.status.notin_(
                [VisitStatus.COMPLETED, VisitStatus.CANCELLED]
            ),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active visit already exists for this patient",
        )

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=current_user.clinic_id,
        patient_id=payload.patient_id,
        assigned_doctor_id=payload.assigned_doctor_id,
        status=VisitStatus.REGISTERED,
        started_at=datetime.utcnow(),  # 🔒 Legal start of care
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)

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

# Get visit details
@router.get(
    "/{visit_id}",
    response_model=VisitResponse,
)
def get_visit(
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

    return visit