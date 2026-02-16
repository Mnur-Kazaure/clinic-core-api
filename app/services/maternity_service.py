# app/services/maternity_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from app.models.maternity_delivery_record import MaternityDeliveryRecord
from app.models.maternity_postnatal_note import MaternityPostnatalNote
from app.models.family_planning_event import FamilyPlanningEvent
from app.models.pregnancy_episode import PregnancyEpisode
from app.models.visit import Visit
from app.services.follow_up_workflow_service import FollowUpWorkflowService
from app.shared.enums import RecordStatus, VisitServiceLine, VisitStatus


class MaternityService:
    def __init__(self, db):
        self.db = db

    def _get_visit_for_maternity(self, *, visit_id: UUID, clinic_id: UUID, actor_id: UUID) -> Visit:
        visit = (
            self.db.query(Visit)
            .filter(
                Visit.id == visit_id,
                Visit.clinic_id == clinic_id,
            )
            .first()
        )
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        if visit.service_line != VisitServiceLine.MATERNITY:
            raise HTTPException(status_code=400, detail="Visit is not maternity")
        if visit.assigned_doctor_id != actor_id:
            raise HTTPException(status_code=403, detail="Visit not assigned to you")
        if visit.status in {VisitStatus.CANCELLED}:
            raise HTTPException(status_code=400, detail="Visit is cancelled")
        return visit

    def get_delivery(
        self, *, clinic_id: UUID, visit_id: UUID, actor_id: UUID
    ) -> MaternityDeliveryRecord | None:
        self._get_visit_for_maternity(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        return (
            self.db.query(MaternityDeliveryRecord)
            .filter(
                MaternityDeliveryRecord.clinic_id == clinic_id,
                MaternityDeliveryRecord.visit_id == visit_id,
            )
            .first()
        )

    def upsert_delivery(
        self,
        *,
        clinic_id: UUID,
        visit_id: UUID,
        actor_id: UUID,
        payload,
    ) -> MaternityDeliveryRecord:
        visit = self._get_visit_for_maternity(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        episode = None
        if payload.episode_id:
            episode = (
                self.db.query(PregnancyEpisode)
                .filter(
                    PregnancyEpisode.id == payload.episode_id,
                    PregnancyEpisode.clinic_id == clinic_id,
                )
                .first()
            )
            if not episode:
                raise HTTPException(status_code=404, detail="Episode not found")

        record = (
            self.db.query(MaternityDeliveryRecord)
            .filter(
                MaternityDeliveryRecord.clinic_id == clinic_id,
                MaternityDeliveryRecord.visit_id == visit_id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if not record:
            record = MaternityDeliveryRecord(
                clinic_id=clinic_id,
                visit_id=visit_id,
                episode_id=episode.id if episode else None,
                recorded_by=actor_id,
                recorded_at=now,
                record_status=RecordStatus.DRAFT,
            )
            self.db.add(record)

        if record.record_status == RecordStatus.SIGNED:
            raise HTTPException(status_code=409, detail="Delivery record already signed")

        record.episode_id = episode.id if episode else None
        record.delivered_at = payload.delivered_at
        record.mode_of_delivery = payload.mode_of_delivery
        record.outcome = payload.outcome
        record.baby_sex = payload.baby_sex
        record.baby_weight_kg = payload.baby_weight_kg
        record.apgar_1 = payload.apgar_1
        record.apgar_5 = payload.apgar_5
        record.maternal_complications = payload.maternal_complications
        record.newborn_complications = payload.newborn_complications
        record.notes = payload.notes

        if payload.action == "SIGN":
            record.record_status = RecordStatus.SIGNED
            record.signed_at = now
            FollowUpWorkflowService(self.db).complete_linked_follow_up_on_visit_sign(
                clinic_id=clinic_id,
                actor_id=actor_id,
                visit_id=visit.id,
                patient_id_canonical=visit.patient_id,
                linked_follow_up_id=visit.linked_follow_up_id,
                signed_at=now,
                commit=False,
            )
        else:
            record.record_status = RecordStatus.DRAFT

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_postnatal_notes(
        self, *, clinic_id: UUID, visit_id: UUID, actor_id: UUID
    ) -> list[MaternityPostnatalNote]:
        self._get_visit_for_maternity(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        return (
            self.db.query(MaternityPostnatalNote)
            .filter(
                MaternityPostnatalNote.clinic_id == clinic_id,
                MaternityPostnatalNote.visit_id == visit_id,
            )
            .order_by(MaternityPostnatalNote.added_at.desc())
            .all()
        )

    def add_postnatal_note(
        self,
        *,
        clinic_id: UUID,
        visit_id: UUID,
        actor_id: UUID,
        payload,
    ) -> MaternityPostnatalNote:
        self._get_visit_for_maternity(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        note = MaternityPostnatalNote(
            clinic_id=clinic_id,
            visit_id=visit_id,
            subject=payload.subject,
            note=payload.note,
            added_by=actor_id,
            added_at=datetime.now(timezone.utc),
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def list_family_planning_events(
        self, *, clinic_id: UUID, visit_id: UUID, actor_id: UUID
    ) -> list[FamilyPlanningEvent]:
        self._get_visit_for_maternity(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        return (
            self.db.query(FamilyPlanningEvent)
            .filter(
                FamilyPlanningEvent.clinic_id == clinic_id,
                FamilyPlanningEvent.visit_id == visit_id,
            )
            .order_by(FamilyPlanningEvent.added_at.desc())
            .all()
        )

    def add_family_planning_event(
        self,
        *,
        clinic_id: UUID,
        visit_id: UUID,
        actor_id: UUID,
        payload,
    ) -> FamilyPlanningEvent:
        self._get_visit_for_maternity(visit_id=visit_id, clinic_id=clinic_id, actor_id=actor_id)
        event = FamilyPlanningEvent(
            clinic_id=clinic_id,
            visit_id=visit_id,
            commodity=payload.commodity,
            notes=payload.notes,
            added_by=actor_id,
            added_at=datetime.now(timezone.utc),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
