# app/services/consultation_service.py
from datetime import datetime, timezone
from uuid import UUID
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
from app.services.follow_up_service import RecallSuggestionService
from app.services.follow_up_workflow_service import FollowUpWorkflowService


class ConsultationService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
        self.recall_suggestion_service = RecallSuggestionService(db)
        self.follow_up_workflow_service = FollowUpWorkflowService(db)

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

        self.event_service.emit(
            event_type="CONSULTATION_STARTED",
            actor_id=user.id,
            actor_role=user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="clinical",
            payload={
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
        *,
        linked_follow_up_id: UUID | None = None,
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
        signed_at = datetime.now(timezone.utc)
        consultation.record_status = RecordStatus.SIGNED
        consultation.signed_at = signed_at

        if linked_follow_up_id is not None:
            consultation.visit.linked_follow_up_id = linked_follow_up_id

        self.follow_up_workflow_service.complete_linked_follow_up_on_visit_sign(
            clinic_id=consultation.visit.clinic_id,
            actor_id=user.id,
            visit_id=consultation.visit.id,
            patient_id_canonical=consultation.visit.patient_id,
            linked_follow_up_id=consultation.visit.linked_follow_up_id,
            signed_at=signed_at,
            commit=False,
        )

        self.db.commit()
        self.db.refresh(consultation)

        suggestions = self.recall_suggestion_service.resolve(
            clinic_id=consultation.visit.clinic_id,
            patient_id=consultation.visit.patient_id,
            diagnosis_text=consultation.diagnosis,
        )
        setattr(consultation, "recall_suggestions", suggestions)

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
