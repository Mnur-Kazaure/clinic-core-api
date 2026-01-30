# app/services/bed_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.shared.enums import AdmissionStatus, BedAssignmentType, BedStatus
from app.services.event_service import EventService
from app.services.access_log_service import AccessLogService


class BedService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
        self.access_log_service = AccessLogService(db)

    def assign_bed(
        self,
        *,
        admission_id: UUID,
        bed_id: UUID,
        actor,
        reason: str | None = None,
        break_glass: bool = False,
        purpose_of_use: str | None = None,
        break_glass_reason: str | None = None,
    ) -> BedAssignment:
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

        bed = (
            self.db.query(Bed)
            .filter(Bed.id == bed_id)
            .first()
        )
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=409, detail="Bed not available")

        if break_glass:
            if not purpose_of_use or not break_glass_reason:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Break-glass requires purpose_of_use and reason",
                )
            self.access_log_service.log_break_glass(
                actor=actor,
                clinic_id=actor.clinic_id,
                patient_id=admission.patient_id,
                purpose_of_use=purpose_of_use,
                reason=break_glass_reason,
            )

        assignment = BedAssignment(
            clinic_id=actor.clinic_id,
            admission_id=admission.id,
            bed_id=bed.id,
            assigned_by=actor.id,
            assignment_type=BedAssignmentType.ASSIGN,
            reason=reason,
            assigned_at=datetime.now(timezone.utc),
        )
        self.db.add(assignment)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bed already assigned",
            )
        self.db.refresh(assignment)

        self.event_service.emit(
            event_type="BED_ASSIGNED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=admission.clinic_id,
            patient_id=admission.patient_id,
            emitter="bed",
            payload={
                "admission_id": str(admission.id),
                "bed_id": str(bed.id),
                "ward_id": str(bed.ward_id),
                "assigned_at": assignment.assigned_at.isoformat(),
                "assignment_type": assignment.assignment_type.value,
            },
        )
        return assignment

    def transfer_bed(
        self,
        *,
        admission_id: UUID,
        to_bed_id: UUID,
        actor,
        reason: str,
        break_glass: bool = False,
        purpose_of_use: str | None = None,
        break_glass_reason: str | None = None,
    ) -> BedAssignment:
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

        current = (
            self.db.query(BedAssignment)
            .filter(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .first()
        )
        if not current:
            raise HTTPException(status_code=409, detail="No active bed assignment")

        new_bed = (
            self.db.query(Bed)
            .filter(Bed.id == to_bed_id)
            .first()
        )
        if not new_bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if new_bed.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if new_bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=409, detail="Bed not available")

        if break_glass:
            if not purpose_of_use or not break_glass_reason:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Break-glass requires purpose_of_use and reason",
                )
            self.access_log_service.log_break_glass(
                actor=actor,
                clinic_id=actor.clinic_id,
                patient_id=admission.patient_id,
                purpose_of_use=purpose_of_use,
                reason=break_glass_reason,
            )

        current.released_at = datetime.now(timezone.utc)
        old_bed = (
            self.db.query(Bed)
            .filter(Bed.id == current.bed_id)
            .first()
        )
        new_assignment = BedAssignment(
            clinic_id=actor.clinic_id,
            admission_id=admission.id,
            bed_id=new_bed.id,
            assigned_by=actor.id,
            assignment_type=BedAssignmentType.TRANSFER,
            reason=reason,
            assigned_at=datetime.now(timezone.utc),
        )
        self.db.add(new_assignment)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bed already assigned",
            )

        self.db.refresh(new_assignment)

        self.event_service.emit(
            event_type="BED_TRANSFERRED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=admission.clinic_id,
            patient_id=admission.patient_id,
            emitter="bed",
            payload={
                "admission_id": str(admission.id),
                "from_bed_id": str(current.bed_id),
                "to_bed_id": str(new_bed.id),
                "from_ward_id": str(old_bed.ward_id) if old_bed else None,
                "to_ward_id": str(new_bed.ward_id),
                "released_at": current.released_at.isoformat(),
                "assigned_at": new_assignment.assigned_at.isoformat(),
                "reason": reason,
            },
        )
        return new_assignment
