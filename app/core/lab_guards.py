# app/core/lab_guards.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth_dev import get_current_user
from app.models.visit import Visit
from app.shared.enums import VisitStatus, UserRole


def require_lab_access(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Role enforcement
    if current_user.role != UserRole.LAB:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lab staff may access lab module",
        )

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

    # Clinic boundary (future multi-tenancy safe)
    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    # 🔒 State guard (THE CORE RULE)
    if visit.status != VisitStatus.LAB_REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lab access denied. Visit is in state {visit.status}",
        )

    return visit