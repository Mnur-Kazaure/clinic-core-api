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
from app.core.dependencies import get_current_user
from app.shared.enums import VisitStatus

from app.models.visit import Visit
from app.schemas.visit import AllowedTransitionsResponse
from app.schemas.visit import VisitTimelineResponse

# app/api/v1/visit.py
# router = APIRouter(prefix="/api/visits", tags=["Visits"])
router = APIRouter(prefix="/visits", tags=["Visits"])



from app.schemas.visit import VisitCreateRequest, VisitCreateResponse

from datetime import datetime
from app.core.rbac import require_reception
import uuid


@router.post(
    "",
    response_model=VisitCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_visit(
    payload: VisitCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=current_user.clinic_id,
        patient_id=payload.patient_id,
        assigned_doctor_id=payload.assigned_doctor_id,
        status=VisitStatus.REGISTERED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)

    return visit




# Transition a visit to a new status
# Idempotent endpoint to prevent duplicate transitions
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

        # 🔒 Clinic boundary (future multi-tenancy safe)
        if visit.clinic_id != current_user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )

        # ✅ Persist idempotency result (CRITICAL)
        db.add(
            IdempotencyKey(
                id=uuid.uuid4(),
                key=key,
                user_id=current_user.id,
                endpoint="VISIT_TRANSITION",
                request_hash=hash_request(payload.dict()),
                response_body=VisitResponse.model_validate(visit).dict(),
            )
        )
        db.commit()

        return visit

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

# Idempotent endpoint to prevent duplicate transitions
# def transition_visit(
#     visit_id: UUID,
#     payload: VisitTransitionRequest,
#     dep=Depends(idempotent("VISIT_TRANSITION")),
#     current_user=Depends(require_visit_access),
# ):
#     record, key, db = dep

#     if record:
#         return record.response_body


#     service = VisitService(db)

#     try:
#         visit = service.transition_visit(
#             visit_id=visit_id,
#             to_status=payload.to_status,
#             user=current_user,
#         )

#         # 🔒 Clinic boundary (future multi-tenancy safe)
#         if visit.clinic_id != current_user.clinic_id:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Cross-clinic access denied",
#             )

#         return visit

#     except PermissionError as e:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail=str(e),
#         )

#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e),
#         )
    

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