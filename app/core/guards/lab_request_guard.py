# app/core/guards/lab_request_guard.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.models.visit import Visit
from app.schemas.lab_request import LabRequestCreate
from app.shared.enums import VisitStatus, UserRole


def require_lab_request_permission(
    payload: LabRequestCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    visit_id = payload.visit_id

# def require_lab_request_permission(
#     visit_id: UUID,
#     db=Depends(get_db),
#     user=Depends(get_current_user),
# ):
    if user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
        )

    visit = db.query(Visit).filter(Visit.id == visit_id).first()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if visit.clinic_id != user.clinic_id:
        raise HTTPException(status_code=403, detail="Cross-clinic access denied")

    if visit.status not in {
        VisitStatus.IN_CONSULTATION,
        VisitStatus.LAB_REQUESTED,
    }:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot order lab when visit is {visit.status}",
        )

    if visit.assigned_doctor_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only assigned doctor may order labs",
        )

    return visit
