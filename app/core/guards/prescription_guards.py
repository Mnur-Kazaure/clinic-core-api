# app/core/guards/prescription_guards.py
from fastapi import Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.models.consultation import Consultation
from app.models.prescription import Prescription
from app.models.visit import Visit

from app.shared.enums import (
    UserRole,
    VisitStatus,
    PrescriptionStatus,
)
from app.schemas.prescription import PrescriptionCreateRequest


# -------------------------------------------------
# Doctor — Issue Prescription
# -------------------------------------------------
def require_doctor_for_prescription(
    payload: PrescriptionCreateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    consultation_id = payload.consultation_id

    # Role enforcement
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
        )

    consultation = (
        db.query(Consultation)
        .filter(Consultation.id == consultation_id)
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    # Ownership
    if consultation.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only assigned doctor may prescribe",
        )

    # 🔒 Visit eligibility invariant (Phase 11.1)
    visit = (
        db.query(Visit)
        .filter(Visit.id == consultation.visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visit.status not in {
        VisitStatus.IN_CONSULTATION,
        VisitStatus.LAB_REQUESTED,
        VisitStatus.LAB_COMPLETED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Visit not eligible for prescription",
        )

    return consultation


# -------------------------------------------------
# Read Access — Doctor / Pharmacy / Pharmacy HOD / Pharmacy Store / Admin
# -------------------------------------------------

def require_prescription_read_access(
    prescription_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
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

    if current_user.role == UserRole.ADMIN:
        return prescription

    if current_user.role in {
        UserRole.PHARMACY,
        UserRole.PHARMACY_HOD,
    }:
        return prescription

    if current_user.role == UserRole.DOCTOR:
        consultation = (
            db.query(Consultation)
            .filter(Consultation.id == prescription.consultation_id)
            .first()
        )
        if consultation and consultation.doctor_id == current_user.id:
            return prescription

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access prescription",
    )


# -------------------------------------------------
# Pharmacy — Dispense Prescription
# -------------------------------------------------

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
            detail="Only ISSUED prescriptions may be dispensed",
        )

    return prescription


# -------------------------------------------------
# Doctor — Cancel Prescription
# -------------------------------------------------

def require_doctor_for_prescription_cancel(
    prescription_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
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
            detail="Only ISSUED prescriptions may be cancelled",
        )

    if prescription.prescribed_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only prescribing doctor may cancel prescription",
        )

    return prescription
