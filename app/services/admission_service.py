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
from app.shared.enums import (
    AdmissionStatus,
    AdmissionType,
    AdmissionDischargeDisposition,
)
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Break-glass not allowed on write operations",
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

    def discharge_admission(
        self,
        *,
        admission_id: UUID,
        actor,
        disposition: AdmissionDischargeDisposition = AdmissionDischargeDisposition.HOME,
        transferred_to_facility: str | None = None,
        death_pronounced_at: datetime | None = None,
        discharge_notes: str | None = None,
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

        if disposition == AdmissionDischargeDisposition.TRANSFERRED_OUT:
            if not transferred_to_facility or len(transferred_to_facility.strip()) < 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="transferred_to_facility is required for TRANSFERRED_OUT",
                )
            if death_pronounced_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="death_pronounced_at must be null for TRANSFERRED_OUT",
                )

        if disposition == AdmissionDischargeDisposition.DECEASED:
            if death_pronounced_at is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="death_pronounced_at is required for DECEASED",
                )
            if transferred_to_facility is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="transferred_to_facility must be null for DECEASED",
                )

        admission.status = AdmissionStatus.DISCHARGED
        admission.discharged_at = datetime.now(timezone.utc)
        admission.discharge_disposition = disposition
        admission.transferred_to_facility = (
            transferred_to_facility.strip()
            if transferred_to_facility is not None
            else None
        )
        admission.death_pronounced_at = death_pronounced_at
        admission.discharge_notes = discharge_notes.strip() if discharge_notes else None

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
                "disposition": admission.discharge_disposition.value if admission.discharge_disposition else None,
                "transferred_to_facility": admission.transferred_to_facility,
                "death_pronounced_at": admission.death_pronounced_at.isoformat() if admission.death_pronounced_at else None,
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

        # Auto-release active bed assignment (cancel can occur after bed assignment)
        active_assignment = (
            self.db.query(BedAssignment)
            .filter(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .first()
        )
        if active_assignment:
            active_assignment.released_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(admission)
        return admission

    def release_admission_bed(
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

        active_assignment = (
            self.db.query(BedAssignment)
            .filter(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .first()
        )
        if active_assignment is None:
            raise HTTPException(status_code=409, detail="No active bed assignment")

        active_assignment.released_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(admission)

        self.event_service.emit(
            event_type="BED_RELEASED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=admission.clinic_id,
            patient_id=admission.patient_id,
            emitter="bed",
            payload={
                "admission_id": str(admission.id),
                "bed_id": str(active_assignment.bed_id),
                "released_at": active_assignment.released_at.isoformat(),
                "reason": reason.strip(),
            },
        )
        return admission
