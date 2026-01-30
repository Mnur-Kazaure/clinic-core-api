# app/core/guards/lab_guards.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.models.visit import Visit
from app.models.lab_request import LabRequest
from app.shared.enums import VisitStatus, UserRole, LabRequestStatus


def require_lab_access(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    # 1️⃣ Role enforcement
    if current_user.role != UserRole.LAB:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lab staff may access lab operations",
        )

    # 2️⃣ Visit existence
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    # 3️⃣ Clinic boundary
    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    # 4️⃣ Visit state enforcement
    if visit.status != VisitStatus.LAB_REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lab access denied. Visit is in state {visit.status}",
        )

    # 5️⃣ LabRequest existence
    lab_request = (
        db.query(LabRequest)
        .filter(LabRequest.visit_id == visit.id)
        .first()
    )

    if not lab_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No lab request exists for this visit",
        )

    # 6️⃣ LabRequest lifecycle enforcement
    if lab_request.status == LabRequestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lab request already completed",
        )

    return visit


def _require_lab_request_access_base(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    *,
    enforce_visit_status: bool,
) -> LabRequest:
    if current_user.role != UserRole.LAB:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab access required",
        )

    lab_request = (
        db.query(LabRequest)
        .filter(LabRequest.id == lab_request_id)
        .first()
    )

    if not lab_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab request not found",
        )

    visit = (
        db.query(Visit)
        .filter(Visit.id == lab_request.visit_id)
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

    if enforce_visit_status and visit.status != VisitStatus.LAB_REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lab access denied. Visit is in state {visit.status}",
        )

    return lab_request


def require_lab_request_access_for_result(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> LabRequest:
    lab_request = _require_lab_request_access_base(
        lab_request_id,
        db=db,
        current_user=current_user,
        enforce_visit_status=True,
    )

    if lab_request.status == LabRequestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lab request already completed",
        )

    return lab_request


def require_lab_request_access_for_complete(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> LabRequest:
    return _require_lab_request_access_base(
        lab_request_id,
        db=db,
        current_user=current_user,
        enforce_visit_status=True,
    )


def require_lab_request_access_for_read(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> LabRequest:
    return _require_lab_request_access_base(
        lab_request_id,
        db=db,
        current_user=current_user,
        enforce_visit_status=False,
    )



def require_lab_user(user=Depends(get_current_user)):
    if user.role != UserRole.LAB:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab access required",
        )
    return user
