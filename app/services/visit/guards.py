# app/services/visit/guards.py

from app.shared.enums import VisitStatus, UserRole
from app.models.visit import Visit
from app.models.lab import LabRequest
from app.models.pharmacy import Prescription
from app.models.prescription import Prescription


ALLOWED_TRANSITIONS = {
    VisitStatus.REGISTERED: [
        VisitStatus.TRIAGED,
        VisitStatus.CANCELLED,
    ],
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
        VisitStatus.TRIAGED,
        VisitStatus.CANCELLED,
    ],
    UserRole.DOCTOR: [
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
        # 🔒 SYSTEM bypass — internal automation only
    if user.role == UserRole.SYSTEM:
        return
    # 1️⃣ No edits after completion
    if visit.status == VisitStatus.COMPLETED:
        raise PermissionError("Visit already completed")

    # 2️⃣ Valid state transition
    allowed_targets = ALLOWED_TRANSITIONS.get(visit.status, [])
    if to_status not in allowed_targets:
        raise ValueError(
            f"Invalid transition from {visit.status} to {to_status}"
        )

    # 3️⃣ Role-based authority
    allowed_for_role = ROLE_TRANSITION_MATRIX.get(user.role, [])
    if to_status not in allowed_for_role:
        raise PermissionError(
            f"Role {user.role} cannot transition visit to {to_status}"
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

    # 5️⃣ Assigned doctor enforcement
    if (
        user.role == UserRole.DOCTOR
        and to_status == VisitStatus.IN_CONSULTATION
        and visit.assigned_doctor_id != user.id
    ):
        raise PermissionError(
            "Only assigned doctor can start consultation"
        )

    # 4️⃣ Clinical invariant (LOCKED RULE)
    if (
        visit.status in {
            VisitStatus.IN_CONSULTATION,
            VisitStatus.LAB_COMPLETED,
        }
        and to_status == VisitStatus.COMPLETED
    ):
        _ensure_no_labs_or_drugs(db, visit)


def _ensure_no_labs_or_drugs(db, visit: Visit):
    lab_count = (
        db.query(LabRequest)
        .filter(LabRequest.visit_id == visit.id)
        .count()
    )

    if lab_count > 0:
        raise PermissionError(
            "Cannot complete visit: lab requests exist"
        )

    prescription_count = (
        db.query(Prescription)
        .filter(Prescription.visit_id == visit.id)
        .count()
    )

    if prescription_count > 0:
        raise PermissionError(
            "Cannot complete visit: prescriptions exist"
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
