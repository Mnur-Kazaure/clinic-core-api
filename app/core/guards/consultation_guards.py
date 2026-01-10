# app/core/guards/consultation_guards.py
from datetime import datetime

from app.models.visit import Visit
from app.models.consultation import Consultation
from app.shared.enums import VisitStatus
from app.shared.enums import UserRole


def ensure_visit_in_consultation(visit: Visit):
    if visit.status != VisitStatus.IN_CONSULTATION:
        raise ValueError(
            "Consultation can only start when visit is IN_CONSULTATION"
        )


def ensure_assigned_doctor(visit: Visit, user):
    if user.role != UserRole.DOCTOR:
        raise PermissionError("Only a doctor can perform consultation")

    if visit.assigned_doctor_id != user.id:
        raise PermissionError(
            "Only the assigned doctor can access this consultation"
        )


def ensure_no_existing_consultation(db, visit_id):
    existing = (
        db.query(Consultation)
        .filter(Consultation.visit_id == visit_id)
        .first()
    )
    if existing:
        raise ValueError(
            "A consultation already exists for this visit"
        )


def ensure_consultation_not_completed(consultation: Consultation):
    if consultation.completed_at is not None:
        raise ValueError("Consultation is already completed")


def mark_consultation_completed(consultation: Consultation):
    consultation.completed_at = datetime.utcnow()
