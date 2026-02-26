# app/services/visit/guards.py

from app.shared.enums import (
    PrescriptionStatus,
    UserRole,
    VisitStatus,
)
from app.models.visit import Visit
from app.models.lab_request import LabRequest
from app.models.prescription import Prescription


def _normalize_role(role) -> UserRole:
    if isinstance(role, UserRole):
        return role
    value = getattr(role, "value", role)
    try:
        return UserRole(str(value))
    except ValueError:
        return UserRole(str(value).replace("UserRole.", ""))


ALLOWED_TRANSITIONS = {
    VisitStatus.REGISTERED: [
        VisitStatus.IN_CONSULTATION,
        VisitStatus.CANCELLED,
    ],
    # Legacy compatibility: allow already-triaged visits to continue flow.
    VisitStatus.TRIAGED: [
        VisitStatus.IN_CONSULTATION,
        VisitStatus.CANCELLED,
    ],
    VisitStatus.IN_CONSULTATION: [
        VisitStatus.LAB_REQUESTED,
        VisitStatus.PHARMACY_PENDING,
        VisitStatus.COMPLETED,
    ],
    VisitStatus.LAB_REQUESTED: [
        VisitStatus.LAB_COMPLETED,
        # Flexible workflow: allow progressing to pharmacy/completion even if labs remain pending.
        VisitStatus.PHARMACY_PENDING,
        VisitStatus.COMPLETED,
    ],
    VisitStatus.LAB_COMPLETED: [
        VisitStatus.PHARMACY_PENDING,
        VisitStatus.COMPLETED,
    ],
    VisitStatus.PHARMACY_PENDING: [
        VisitStatus.COMPLETED,
    ],
}


ROLE_TRANSITION_MATRIX = {
    UserRole.RECEPTION: [
        VisitStatus.CANCELLED,
        # Flexible workflow: Reception can complete visits (normal or override).
        VisitStatus.COMPLETED,
    ],
    UserRole.DOCTOR: [
        VisitStatus.IN_CONSULTATION,
        VisitStatus.LAB_REQUESTED,
        VisitStatus.PHARMACY_PENDING,
        VisitStatus.COMPLETED,
    ],
    UserRole.CHEW: [
        VisitStatus.IN_CONSULTATION,
        VisitStatus.LAB_REQUESTED,
        VisitStatus.PHARMACY_PENDING,
        VisitStatus.COMPLETED,
    ],
    UserRole.MIDWIFE: [
        VisitStatus.IN_CONSULTATION,
        VisitStatus.LAB_REQUESTED,
        VisitStatus.PHARMACY_PENDING,
        VisitStatus.COMPLETED,
    ],
    UserRole.LAB: [
        VisitStatus.LAB_COMPLETED,
    ],
    UserRole.PHARMACY: [
        VisitStatus.COMPLETED,
    ],
    UserRole.ADMIN: list(VisitStatus),
}


def guard_can_transition(db, visit: Visit, to_status: VisitStatus, user):
    role = _normalize_role(user.role)
    # 🔒 SYSTEM bypass — internal automation only
    if role == UserRole.SYSTEM:
        return
    # 1️⃣ No edits after completion
    if visit.status == VisitStatus.COMPLETED:
        raise PermissionError("Visit already completed")

    # TRIAGED visit status is retired; triage is tracked via triage_state.
    if to_status == VisitStatus.TRIAGED:
        raise PermissionError("TRIAGE_STATUS_RETIRED")

    # 2️⃣ Valid state transition
    allowed_targets = ALLOWED_TRANSITIONS.get(visit.status, [])
    if to_status not in allowed_targets:
        raise ValueError(
            f"Invalid transition from {visit.status} to {to_status}"
        )

    # 3️⃣ Role-based authority
    allowed_for_role = ROLE_TRANSITION_MATRIX.get(role, [])
    if to_status not in allowed_for_role:
        raise PermissionError(
            f"Role {role} cannot transition visit to {to_status}"
        )

    # 3️⃣ Lab request must exist before marking visit as LAB_REQUESTED
    if to_status == VisitStatus.LAB_REQUESTED:
        lab_count = (
            db.query(LabRequest)
            .filter(LabRequest.visit_id == visit.id)
            .count()
        )
        if lab_count == 0:
            raise PermissionError(
                "Cannot request labs: no lab order exists for this visit"
            )

    if to_status == VisitStatus.PHARMACY_PENDING:
        prescription_count = (
            db.query(Prescription)
            .filter(Prescription.visit_id == visit.id)
            .filter(Prescription.status == PrescriptionStatus.ISSUED)
            .count()
        )
        if prescription_count == 0:
            raise PermissionError(
                "Cannot send to pharmacy: no prescriptions issued"
            )

    # 5️⃣ Assigned doctor enforcement
    if (
        role in {UserRole.DOCTOR, UserRole.CHEW, UserRole.MIDWIFE}
        and to_status == VisitStatus.IN_CONSULTATION
        and visit.assigned_doctor_id != user.id
    ):
        raise PermissionError(
            "Only assigned clinical owner can start consultation"
        )

def _ensure_prescriptions_exist(db, visit: Visit):
    count = (
        db.query(Prescription)
        .filter(Prescription.visit_id == visit.id)
        .count()
    )

    if count == 0:
        raise PermissionError(
            "Cannot complete visit: no prescriptions issued"
        )
