# app/core/guards/user_guards.py
from app.models.user import User
from app.shared.enums import UserRole, VisitServiceLine


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


def ensure_owner_for_service_line(db, owner_id, clinic_id, service_line: VisitServiceLine):
    """
    Validate the assigned owner for a visit based on service line.
    OPD -> DOCTOR
    ANC -> CHEW
    MATERNITY -> MIDWIFE
    """
    role_map = {
        VisitServiceLine.OPD: UserRole.DOCTOR,
        VisitServiceLine.ANC: UserRole.CHEW,
        VisitServiceLine.MATERNITY: UserRole.MIDWIFE,
    }
    expected_role = role_map.get(service_line)
    if not expected_role:
        raise ValueError("Invalid service line")

    owner = (
        db.query(User)
        .filter(
            User.id == owner_id,
            User.clinic_id == clinic_id,
            User.role == expected_role.value,
            User.is_active == True,
        )
        .first()
    )
    if not owner:
        raise ValueError("Assigned owner not found in clinic for service line")
    return owner
