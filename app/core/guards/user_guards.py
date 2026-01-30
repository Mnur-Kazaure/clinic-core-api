# app/core/guards/user_guards.py
from app.models.user import User
from app.shared.enums import UserRole


def ensure_doctor_in_clinic(db, doctor_id, clinic_id):
    doctor = (
        db.query(User)
        .filter(
            User.id == doctor_id,
            User.clinic_id == clinic_id,
            User.role == UserRole.DOCTOR.value,
 #           User.role == UserRole.DOCTOR,
            User.is_active == True,
        )
        .first()
    )
    if not doctor:
        raise ValueError("Assigned doctor not found in clinic")
    return doctor
