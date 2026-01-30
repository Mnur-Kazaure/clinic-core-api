# app/core/guards/doctor_lab_guards.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.lab_request import LabRequest
from app.models.visit import Visit
from app.shared.enums import UserRole


def _ensure_doctor_visit_access(visit: Visit, current_user) -> None:
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
        )

    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    if visit.assigned_doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only assigned doctor may access lab results",
        )


def require_doctor_lab_requests_by_visit(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> Visit:
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

    _ensure_doctor_visit_access(visit, current_user)
    return visit


def require_doctor_lab_request_access(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> LabRequest:
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

    _ensure_doctor_visit_access(visit, current_user)
    return lab_request
