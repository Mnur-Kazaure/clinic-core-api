# app/core/guards/pharmacy_prescription_guards.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.models.prescription import Prescription
from app.models.dispensation import Dispensation
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent
from app.models.visit import Visit
from app.shared.enums import UserRole, PrescriptionStatus, VisitStatus


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

    existing_fulfillment = (
        db.query(PrescriptionFulfillmentEvent)
        .filter(
            PrescriptionFulfillmentEvent.prescription_id == prescription.id,
            PrescriptionFulfillmentEvent.clinic_id == prescription.clinic_id,
        )
        .first()
    )
    if existing_fulfillment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prescription already dispensed",
        )

    existing = (
        db.query(Dispensation)
        .filter(Dispensation.prescription_id == prescription.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prescription already dispensed",
        )

    visit = (
        db.query(Visit)
        .filter(Visit.id == prescription.visit_id)
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

    # Flexible workflow: pharmacy dispensing is allowed even if the visit is completed,
    # as long as the visit is not cancelled.
    if visit.status == VisitStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pharmacy access denied. Visit is CANCELLED",
        )

    return prescription
