# app/services/admission_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.bed_assignment import BedAssignment
from app.models.bed import Bed
from app.models.patient import Patient
from app.shared.enums import AdmissionStatus, AdmissionType
from app.services.event_service import EventService
from app.services.access_log_service import AccessLogService


class AdmissionService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
        self.access_log_service = AccessLogService(db)

    def create_admission(
        self,
        *,
        patient_id: UUID,
        admission_type: AdmissionType,
        actor,
        break_glass: bool = False,
        purpose_of_use: str | None = None,
        reason: str | None = None,
    ) -> Admission:
        patient = (
            self.db.query(Patient)
            .filter(Patient.id == patient_id)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if patient.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")

        existing = (
            self.db.query(Admission)
            .filter(
                Admission.patient_id == patient_id,
                Admission.clinic_id == actor.clinic_id,
                Admission.status == AdmissionStatus.ACTIVE,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active admission already exists for this patient",
            )

        if break_glass:
            if not purpose_of_use or not reason:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Break-glass requires purpose_of_use and reason",
                )
            self.access_log_service.log_break_glass(
                actor=actor,
                clinic_id=actor.clinic_id,
                patient_id=patient_id,
                purpose_of_use=purpose_of_use,
                reason=reason,
            )

        admission = Admission(
            clinic_id=actor.clinic_id,
            patient_id=patient_id,
            admission_type=admission_type,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        self.db.add(admission)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise

        self.db.refresh(admission)

        self.event_service.emit(
            event_type="PATIENT_ADMITTED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=actor.clinic_id,
            patient_id=patient_id,
            emitter="admission",
            payload={
                "admission_id": str(admission.id),
                "admission_type": admission_type.value,
                "status": admission.status.value,
                "admitted_at": admission.admitted_at.isoformat(),
            },
        )
        return admission

    def discharge_admission(self, *, admission_id: UUID, actor) -> Admission:
        admission = (
            self.db.query(Admission)
            .filter(Admission.id == admission_id)
            .first()
        )
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        if admission.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if admission.status != AdmissionStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="Admission not active")

        admission.status = AdmissionStatus.DISCHARGED
        admission.discharged_at = datetime.now(timezone.utc)

        # Auto-release active bed assignment
        active_assignment = (
            self.db.query(BedAssignment)
            .filter(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .first()
        )
        bed_release_payload = None
        if active_assignment:
            active_assignment.released_at = datetime.now(timezone.utc)
            bed = (
                self.db.query(Bed)
                .filter(Bed.id == active_assignment.bed_id)
                .first()
            )
            bed_release_payload = {
                "bed_id": str(active_assignment.bed_id),
                "ward_id": str(bed.ward_id) if bed else None,
                "released_at": active_assignment.released_at.isoformat(),
                "release_reason": "discharge",
            }

        self.db.commit()
        self.db.refresh(admission)

        self.event_service.emit(
            event_type="PATIENT_DISCHARGED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=admission.clinic_id,
            patient_id=admission.patient_id,
            emitter="admission",
            payload={
                "admission_id": str(admission.id),
                "status": admission.status.value,
                "discharged_at": admission.discharged_at.isoformat(),
                "bed_release": bed_release_payload,
            },
        )
        return admission

    def cancel_admission(
        self,
        *,
        admission_id: UUID,
        actor,
        reason: str,
    ) -> Admission:
        admission = (
            self.db.query(Admission)
            .filter(Admission.id == admission_id)
            .first()
        )
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        if admission.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if admission.status != AdmissionStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="Admission not active")

        admission.status = AdmissionStatus.CANCELLED
        admission.cancelled_at = datetime.now(timezone.utc)
        admission.cancel_reason = reason

        self.db.commit()
        self.db.refresh(admission)
        return admission
