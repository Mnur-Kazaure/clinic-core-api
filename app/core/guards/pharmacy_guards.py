# app/core/pharmacy_guards.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.models.visit import Visit
from app.shared.enums import VisitStatus, UserRole


def require_pharmacy_user(user=Depends(get_current_user)):
    if user.role != UserRole.PHARMACY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy access required",
        )
    return user


def require_pharmacy_inventory_user(user=Depends(get_current_user)):
    if user.role not in {
        UserRole.PHARMACY_HOD,
        UserRole.PHARMACY_STORE_OFFICER,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy inventory access required",
        )
    return user


def require_pharmacy_access(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Role enforcement
    if current_user.role != UserRole.PHARMACY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pharmacy users may access prescription operations",
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

    # Clinic boundary (future multi-tenant safe)
    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    # Flexible workflow: pharmacy access is prescription-driven, not visit-status-driven.
    # We only hard-block cancelled visits.
    if visit.status == VisitStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pharmacy access denied. Visit is CANCELLED",
        )

    return visit
