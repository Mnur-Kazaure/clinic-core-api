# app/core/guards/patient_guards.py
from fastapi import HTTPException, status
from app.shared.enums import UserRole
from app.models.patient import Patient


def require_reception_role(current_user):
    """
    Ensure the current user has RECEPTION role.
    """
    if current_user.role != UserRole.RECEPTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Reception may create patients",
        )


def ensure_patient_in_clinic(db, patient_id, clinic_id):
    patient = (
        db.query(Patient)
        .filter(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
        )
        .first()
    )
    if not patient:
        raise ValueError("Patient not found in clinic")
    return patient
