# app/core/guards/pharmacy_prescription_guards.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.models.prescription import Prescription
from app.shared.enums import UserRole, PrescriptionStatus


def require_pharmacy_for_dispense(
    prescription_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != UserRole.PHARMACY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy access required",
        )

    prescription = (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id)
        .first()
    )

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    if prescription.status != PrescriptionStatus.ISSUED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prescription is not available for dispensing",
        )

    return prescription