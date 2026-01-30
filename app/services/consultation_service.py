# app/services/consultation_service.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.visit import Visit
from app.models.consultation import Consultation
from app.core.guards.consultation_guards import (
    ensure_visit_in_consultation,
    ensure_assigned_doctor,
    ensure_no_existing_consultation,
    ensure_consultation_not_completed,
    mark_consultation_completed,
)
from app.shared.enums import RecordStatus
from app.services.event_service import EventService


class ConsultationService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    # ─────────────────────────────────────────
    # START CONSULTATION
    # ─────────────────────────────────────────
    def start_consultation(self, visit: Visit, user) -> Consultation:
        """
        Creates a consultation for a visit.

        Preconditions:
        - Visit must be IN_CONSULTATION
        - Doctor must be assigned doctor
        - No existing consultation for visit
        """

        ensure_visit_in_consultation(visit)
        ensure_assigned_doctor(visit, user)
        ensure_no_existing_consultation(self.db, visit.id)

        consultation = Consultation(
            visit_id=visit.id,
            clinic_id=visit.clinic_id,
            doctor_id=user.id,
            started_at=datetime.now(timezone.utc),
            record_status=RecordStatus.DRAFT,
        )

        self.db.add(consultation)
        self.db.commit()
        self.db.refresh(consultation)

        self.event_service.emit(
            event_type="ENTRY_DRAFTED",
            actor_id=user.id,
            actor_role=user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="clinical",
            payload={
                "entity": "consultation",
                "consultation_id": str(consultation.id),
                "visit_id": str(visit.id),
            },
        )

        return consultation

    # ─────────────────────────────────────────
    # UPDATE CONSULTATION (NOTES ONLY)
    # ─────────────────────────────────────────
    def update_consultation(
        self,
        consultation: Consultation,
        user,
        *,
        vitals: str | None = None,
        presenting_complaints: str | None = None,
        diagnosis: str | None = None,
        notes: str | None = None,
        doctor_full_name: str | None = None,
    ) -> Consultation:
        """
        Updates mutable clinical content.

        Preconditions:
        - Doctor must own consultation
        - Consultation must not be completed
        """

        ensure_assigned_doctor(consultation.visit, user)
        ensure_consultation_not_completed(consultation)

        if vitals is not None:
            consultation.vitals = vitals

        if presenting_complaints is not None:
            consultation.presenting_complaints = presenting_complaints

        if diagnosis is not None:
            consultation.diagnosis = diagnosis

        if notes is not None:
            consultation.notes = notes

        if doctor_full_name is not None:
            consultation.doctor_full_name = doctor_full_name

        self.db.commit()
        self.db.refresh(consultation)

        self.event_service.emit(
            event_type="ENTRY_AMENDED",
            actor_id=user.id,
            actor_role=user.role,
            clinic_id=consultation.visit.clinic_id,
            patient_id=consultation.visit.patient_id,
            emitter="clinical",
            payload={
                "entity": "consultation",
                "consultation_id": str(consultation.id),
                "visit_id": str(consultation.visit.id),
            },
        )

        return consultation

    # ─────────────────────────────────────────
    # COMPLETE CONSULTATION
    # ─────────────────────────────────────────
    def complete_consultation(
        self,
        consultation: Consultation,
        user,
    ) -> Consultation:
        """
        Completes a consultation.

        NOTE:
        - Does NOT transition Visit
        - Visit transition remains explicit elsewhere
        """

        ensure_assigned_doctor(consultation.visit, user)
        ensure_consultation_not_completed(consultation)

        mark_consultation_completed(consultation)
        consultation.record_status = RecordStatus.SIGNED
        consultation.signed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(consultation)

        self.event_service.emit(
            event_type="ENTRY_SIGNED",
            actor_id=user.id,
            actor_role=user.role,
            clinic_id=consultation.visit.clinic_id,
            patient_id=consultation.visit.patient_id,
            emitter="clinical",
            payload={
                "entity": "consultation",
                "consultation_id": str(consultation.id),
                "visit_id": str(consultation.visit.id),
            },
        )

        return consultation
    
    def get_by_visit(self, visit_id):
        return (
            self.db.query(Consultation)
            .filter(Consultation.visit_id == visit_id)
            .first()
        )
