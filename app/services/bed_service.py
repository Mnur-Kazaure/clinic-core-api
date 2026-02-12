# app/services/bed_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.models.ward import Ward
from app.shared.enums import AdmissionStatus, BedAssignmentType, BedStatus, WardType
from app.services.event_service import EventService
from app.services.access_log_service import AccessLogService


class BedService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
        self.access_log_service = AccessLogService(db)

    def list_wards(
        self,
        *,
        clinic_id: UUID,
    ) -> list[Ward]:
        return (
            self.db.query(Ward)
            .filter(
                Ward.clinic_id == clinic_id,
                Ward.active.is_(True),
            )
            .order_by(Ward.name.asc())
            .all()
        )

    def list_beds(
        self,
        *,
        clinic_id: UUID,
        available_only: bool = False,
        ward_id: UUID | None = None,
    ) -> list[Bed]:
        query = self.db.query(Bed).filter(
            Bed.clinic_id == clinic_id,
            Bed.active.is_(True),
        )

        if ward_id is not None:
            query = query.filter(Bed.ward_id == ward_id)

        if available_only:
            query = (
                query.outerjoin(
                    BedAssignment,
                    and_(
                        BedAssignment.bed_id == Bed.id,
                        BedAssignment.clinic_id == clinic_id,
                        BedAssignment.released_at.is_(None),
                    ),
                )
                .filter(
                    Bed.status == BedStatus.AVAILABLE,
                    BedAssignment.id.is_(None),
                )
            )

        return query.order_by(Bed.bed_label.asc()).all()

    def create_ward(
        self,
        *,
        clinic_id: UUID,
        name: str,
        ward_type: WardType,
    ) -> Ward:
        existing = (
            self.db.query(Ward.id)
            .filter(
                Ward.clinic_id == clinic_id,
                Ward.name == name,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ward name already exists in clinic",
            )

        ward = Ward(
            clinic_id=clinic_id,
            name=name,
            ward_type=ward_type,
            active=True,
        )
        self.db.add(ward)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ward name already exists in clinic",
            )
        self.db.refresh(ward)
        return ward

    def create_bed(
        self,
        *,
        clinic_id: UUID,
        ward_id: UUID,
        bed_label: str,
        status_value: BedStatus,
    ) -> Bed:
        ward = (
            self.db.query(Ward)
            .filter(Ward.id == ward_id)
            .first()
        )
        if not ward:
            raise HTTPException(status_code=404, detail="Ward not found")
        if ward.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")

        existing = (
            self.db.query(Bed.id)
            .filter(
                Bed.clinic_id == clinic_id,
                Bed.ward_id == ward_id,
                Bed.bed_label == bed_label,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bed label already exists in ward",
            )

        bed = Bed(
            clinic_id=clinic_id,
            ward_id=ward_id,
            bed_label=bed_label,
            status=status_value,
            active=True,
        )
        self.db.add(bed)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bed label already exists in ward",
            )
        self.db.refresh(bed)
        return bed

    def assign_bed(
        self,
        *,
        admission_id: UUID,
        bed_id: UUID,
        actor,
        reason: str | None = None,
        break_glass: bool = False,
        purpose_of_use: str | None = None,
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

        active_assignment = (
            self.db.query(BedAssignment)
            .filter(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .first()
        )
        if active_assignment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Admission already has an active bed assignment; use transfer",
            )

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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Break-glass not allowed on write operations",
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Break-glass not allowed on write operations",
            )

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
        if current.bed_id == new_bed.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transfer target must differ from current bed",
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
