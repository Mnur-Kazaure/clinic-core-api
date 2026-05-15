# app/services/bed_service.py
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, func, or_, cast, String
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.user import User
from app.models.ward import Ward
from app.schemas.ward import (
    WardBedRangePreviewRequest,
    WardBedRangePreviewResponse,
    WardBedRangeCreateRequest,
    WardBedRangeCreateResponse,
    WardAppendBedResponse,
    WardRetireBedResponse,
)
from app.shared.enums import AdmissionStatus, BedAssignmentType, BedStatus, MRNStatus, WardType
from app.services.event_service import EventService


class BedService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    MAX_RANGE_BEDS = 200

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        cleaned = prefix.strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Label prefix is required",
            )
        return cleaned

    @staticmethod
    def _format_label(prefix: str, number: int, padding: int) -> str:
        if padding > 0:
            return f"{prefix}{str(number).zfill(padding)}"
        return f"{prefix}{number}"

    def _generate_labels(
        self, *, prefix: str, start: int, end: int, padding: int
    ) -> list[str]:
        if end < start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Label range end must be greater than or equal to start",
            )
        total = end - start + 1
        if total > self.MAX_RANGE_BEDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Label range exceeds max of {self.MAX_RANGE_BEDS} beds",
            )
        return [
            self._format_label(prefix, number, padding)
            for number in range(start, end + 1)
        ]

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
                query.join(
                    Ward,
                    and_(
                        Ward.id == Bed.ward_id,
                        Ward.clinic_id == Bed.clinic_id,
                    ),
                )
                .outerjoin(
                    BedAssignment,
                    and_(
                        BedAssignment.bed_id == Bed.id,
                        BedAssignment.clinic_id == clinic_id,
                        BedAssignment.released_at.is_(None),
                    ),
                )
                .filter(
                    Bed.status == BedStatus.AVAILABLE,
                    Ward.active.is_(True),
                    BedAssignment.id.is_(None),
                )
            )

        return query.order_by(Bed.bed_label.asc()).all()

    def get_bed_board(
        self,
        *,
        clinic_id: UUID,
    ) -> dict:
        wards = (
            self.db.query(Ward)
            .filter(Ward.clinic_id == clinic_id)
            .order_by(Ward.name.asc())
            .all()
        )
        beds = (
            self.db.query(Bed)
            .filter(Bed.clinic_id == clinic_id)
            .order_by(Bed.ward_id.asc(), Bed.bed_label.asc())
            .all()
        )
        active_assignments = (
            self.db.query(
                BedAssignment.id.label("assignment_id"),
                BedAssignment.bed_id.label("bed_id"),
                BedAssignment.admission_id.label("admission_id"),
                BedAssignment.assigned_at.label("assigned_at"),
                Admission.patient_id.label("patient_id"),
                Patient.full_name.label("patient_name"),
                PatientMRN.mrn.label("patient_mrn"),
            )
            .join(
                Admission,
                and_(
                    Admission.id == BedAssignment.admission_id,
                    Admission.clinic_id == BedAssignment.clinic_id,
                ),
            )
            .outerjoin(
                Patient,
                and_(
                    Patient.id == Admission.patient_id,
                    Patient.clinic_id == Admission.clinic_id,
                ),
            )
            .outerjoin(
                PatientMRN,
                and_(
                    PatientMRN.patient_id == Admission.patient_id,
                    PatientMRN.clinic_id == Admission.clinic_id,
                    PatientMRN.status == MRNStatus.ACTIVE,
                ),
            )
            .filter(
                BedAssignment.clinic_id == clinic_id,
                BedAssignment.released_at.is_(None),
            )
            .order_by(BedAssignment.assigned_at.desc())
            .all()
        )

        assignment_by_bed: dict[UUID, object] = {}
        for row in active_assignments:
            if row.bed_id not in assignment_by_bed:
                assignment_by_bed[row.bed_id] = row

        ward_payload: dict[UUID, dict] = {}
        for ward in wards:
            ward_payload[ward.id] = {
                "summary": {
                    "ward_id": ward.id,
                    "ward_name": ward.name,
                    "ward_type": ward.ward_type,
                    "ward_active": ward.active,
                    "total_beds": 0,
                    "available_beds": 0,
                    "occupied_beds": 0,
                    "out_of_service_beds": 0,
                    "inactive_beds": 0,
                },
                "beds": [],
            }

        beds_by_ward: dict[UUID, list[Bed]] = defaultdict(list)
        for bed in beds:
            beds_by_ward[bed.ward_id].append(bed)

        totals = {
            "total_beds": 0,
            "available_beds": 0,
            "occupied_beds": 0,
            "out_of_service_beds": 0,
            "inactive_beds": 0,
        }

        for ward in wards:
            ward_entry = ward_payload[ward.id]
            for bed in beds_by_ward.get(ward.id, []):
                assignment = assignment_by_bed.get(bed.id)
                if assignment is not None:
                    occupancy_status = "OCCUPIED"
                elif not bed.active:
                    occupancy_status = "INACTIVE"
                elif bed.status == BedStatus.OUT_OF_SERVICE:
                    occupancy_status = "OUT_OF_SERVICE"
                else:
                    occupancy_status = "AVAILABLE"

                occupant = None
                active_assignment_id = None
                if assignment is not None:
                    active_assignment_id = assignment.assignment_id
                    occupant = {
                        "admission_id": assignment.admission_id,
                        "patient_id": assignment.patient_id,
                        "patient_name": assignment.patient_name,
                        "patient_mrn": assignment.patient_mrn,
                        "assigned_at": assignment.assigned_at,
                    }

                ward_entry["beds"].append(
                    {
                        "bed_id": bed.id,
                        "bed_label": bed.bed_label,
                        "bed_status": bed.status,
                        "bed_active": bed.active,
                        "occupancy_status": occupancy_status,
                        "active_assignment_id": active_assignment_id,
                        "occupant": occupant,
                    }
                )
                ward_entry["summary"]["total_beds"] += 1
                totals["total_beds"] += 1
                if occupancy_status == "AVAILABLE":
                    ward_entry["summary"]["available_beds"] += 1
                    totals["available_beds"] += 1
                elif occupancy_status == "OCCUPIED":
                    ward_entry["summary"]["occupied_beds"] += 1
                    totals["occupied_beds"] += 1
                elif occupancy_status == "OUT_OF_SERVICE":
                    ward_entry["summary"]["out_of_service_beds"] += 1
                    totals["out_of_service_beds"] += 1
                else:
                    ward_entry["summary"]["inactive_beds"] += 1
                    totals["inactive_beds"] += 1

            ward_entry["beds"].sort(key=lambda row: row["bed_label"])

        return {
            "wards": [ward_payload[ward.id] for ward in wards],
            "totals": totals,
        }

    def list_occupied_beds(
        self,
        *,
        clinic_id: UUID,
        query: str | None = None,
        ward_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        base = (
            self.db.query(
                BedAssignment.admission_id.label("admission_id"),
                BedAssignment.assigned_at.label("assigned_at"),
                Admission.admission_type.label("admission_type"),
                Bed.id.label("bed_id"),
                Bed.bed_label.label("bed_label"),
                Ward.id.label("ward_id"),
                Ward.name.label("ward_name"),
                Patient.id.label("patient_id"),
                Patient.full_name.label("patient_name"),
                PatientMRN.mrn.label("patient_mrn"),
            )
            .join(
                Bed,
                and_(
                    Bed.id == BedAssignment.bed_id,
                    Bed.clinic_id == BedAssignment.clinic_id,
                ),
            )
            .join(
                Ward,
                and_(
                    Ward.id == Bed.ward_id,
                    Ward.clinic_id == Bed.clinic_id,
                ),
            )
            .join(
                Admission,
                and_(
                    Admission.id == BedAssignment.admission_id,
                    Admission.clinic_id == BedAssignment.clinic_id,
                ),
            )
            .outerjoin(
                Patient,
                and_(
                    Patient.id == Admission.patient_id,
                    Patient.clinic_id == Admission.clinic_id,
                ),
            )
            .outerjoin(
                PatientMRN,
                and_(
                    PatientMRN.patient_id == Admission.patient_id,
                    PatientMRN.clinic_id == Admission.clinic_id,
                    PatientMRN.status == MRNStatus.ACTIVE,
                ),
            )
            .filter(
                BedAssignment.clinic_id == clinic_id,
                BedAssignment.released_at.is_(None),
            )
        )

        if ward_id is not None:
            base = base.filter(Ward.id == ward_id)

        if query:
            q = f"%{query.strip().lower()}%"
            base = base.filter(
                or_(
                    func.lower(Patient.full_name).like(q),
                    func.lower(PatientMRN.mrn).like(q),
                    func.lower(Bed.bed_label).like(q),
                    cast(Patient.id, String).ilike(q),
                )
            )

        total = base.count()
        rows = (
            base.order_by(BedAssignment.assigned_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        items = [
            {
                "bed_id": row.bed_id,
                "bed_label": row.bed_label,
                "ward_id": row.ward_id,
                "ward_name": row.ward_name,
                "admission_id": row.admission_id,
                "admission_type": row.admission_type,
                "patient_id": row.patient_id,
                "patient_name": row.patient_name,
                "patient_mrn": row.patient_mrn,
                "assigned_at": row.assigned_at,
            }
            for row in rows
        ]

        return {"total": total, "items": items}

    def get_occupied_bed_detail(
        self,
        *,
        clinic_id: UUID,
        admission_id: UUID,
    ) -> dict:
        admission = (
            self.db.query(Admission)
            .filter(
                Admission.id == admission_id,
                Admission.clinic_id == clinic_id,
            )
            .first()
        )
        if admission is None:
            raise HTTPException(status_code=404, detail="Admission not found")

        patient = (
            self.db.query(Patient)
            .filter(
                Patient.id == admission.patient_id,
                Patient.clinic_id == clinic_id,
            )
            .first()
        )
        patient_mrn = (
            self.db.query(PatientMRN.mrn)
            .filter(
                PatientMRN.patient_id == admission.patient_id,
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .scalar()
        )

        timeline_rows = (
            self.db.query(
                BedAssignment.id.label("assignment_id"),
                BedAssignment.assignment_type.label("assignment_type"),
                BedAssignment.bed_id.label("bed_id"),
                Bed.bed_label.label("bed_label"),
                Ward.id.label("ward_id"),
                Ward.name.label("ward_name"),
                BedAssignment.assigned_at.label("assigned_at"),
                BedAssignment.released_at.label("released_at"),
                BedAssignment.reason.label("reason"),
                BedAssignment.assigned_by.label("assigned_by"),
                User.full_name.label("assigned_by_name"),
            )
            .join(
                Bed,
                and_(
                    Bed.id == BedAssignment.bed_id,
                    Bed.clinic_id == BedAssignment.clinic_id,
                ),
            )
            .join(
                Ward,
                and_(
                    Ward.id == Bed.ward_id,
                    Ward.clinic_id == Bed.clinic_id,
                ),
            )
            .outerjoin(User, User.id == BedAssignment.assigned_by)
            .filter(
                BedAssignment.clinic_id == clinic_id,
                BedAssignment.admission_id == admission_id,
            )
            .order_by(BedAssignment.assigned_at.asc(), BedAssignment.id.asc())
            .all()
        )

        timeline_items = [
            {
                "assignment_id": row.assignment_id,
                "assignment_type": row.assignment_type,
                "bed_id": row.bed_id,
                "bed_label": row.bed_label,
                "ward_id": row.ward_id,
                "ward_name": row.ward_name,
                "assigned_at": row.assigned_at,
                "released_at": row.released_at,
                "reason": row.reason,
                "assigned_by": row.assigned_by,
                "assigned_by_name": row.assigned_by_name,
                "from_bed_label": None,
            }
            for row in timeline_rows
        ]

        active_assignment = next(
            (row for row in timeline_rows if row.released_at is None), None
        )

        return {
            "admission_id": admission.id,
            "admission_type": admission.admission_type,
            "patient_id": admission.patient_id,
            "patient_name": patient.full_name if patient else None,
            "patient_mrn": patient_mrn,
            "ward_name": active_assignment.ward_name if active_assignment else None,
            "bed_label": active_assignment.bed_label if active_assignment else None,
            "assigned_at": active_assignment.assigned_at if active_assignment else None,
            "timeline": timeline_items,
        }

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

    def preview_ward_bed_range(
        self,
        *,
        clinic_id: UUID,
        payload: WardBedRangePreviewRequest,
    ) -> WardBedRangePreviewResponse:
        prefix = self._normalize_prefix(payload.label_prefix)
        labels = self._generate_labels(
            prefix=prefix,
            start=payload.label_from,
            end=payload.label_to,
            padding=payload.label_padding,
        )
        conflicts: list[str] = []
        existing = (
            self.db.query(Ward.id)
            .filter(Ward.clinic_id == clinic_id, Ward.name == payload.name)
            .first()
        )
        if existing:
            conflicts.append("WARD_NAME_EXISTS")

        return WardBedRangePreviewResponse(
            name=payload.name,
            ward_type=payload.ward_type,
            label_prefix=prefix,
            label_from=payload.label_from,
            label_to=payload.label_to,
            label_padding=payload.label_padding,
            total_beds=len(labels),
            bed_labels=labels,
            conflicts=conflicts,
            is_valid=len(conflicts) == 0,
        )

    def create_ward_with_bed_range(
        self,
        *,
        clinic_id: UUID,
        payload: WardBedRangeCreateRequest,
    ) -> WardBedRangeCreateResponse:
        prefix = self._normalize_prefix(payload.label_prefix)
        labels = self._generate_labels(
            prefix=prefix,
            start=payload.label_from,
            end=payload.label_to,
            padding=payload.label_padding,
        )
        existing = (
            self.db.query(Ward.id)
            .filter(Ward.clinic_id == clinic_id, Ward.name == payload.name)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ward name already exists in clinic",
            )

        ward = Ward(
            clinic_id=clinic_id,
            name=payload.name,
            ward_type=payload.ward_type,
            active=True,
            bed_label_prefix=prefix,
            bed_label_padding=payload.label_padding,
            bed_label_next=payload.label_to + 1,
        )
        self.db.add(ward)
        self.db.flush()

        beds = [
            Bed(
                clinic_id=clinic_id,
                ward_id=ward.id,
                bed_label=label,
                status=BedStatus.AVAILABLE,
                active=True,
            )
            for label in labels
        ]
        self.db.add_all(beds)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bed label already exists in ward",
            )
        self.db.refresh(ward)
        return WardBedRangeCreateResponse(
            ward=ward,
            created_beds=len(labels),
            bed_labels=labels,
        )

    def append_next_bed(
        self,
        *,
        clinic_id: UUID,
        ward_id: UUID,
        actor,
    ) -> WardAppendBedResponse:
        ward = (
            self.db.query(Ward)
            .filter(Ward.id == ward_id)
            .with_for_update()
            .first()
        )
        if ward is None:
            raise HTTPException(status_code=404, detail="Ward not found")
        if ward.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not ward.active:
            raise HTTPException(status_code=409, detail="Ward is inactive")
        if not ward.bed_label_prefix or ward.bed_label_next is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ward is not configured for bed-range expansion",
            )

        label = self._format_label(
            ward.bed_label_prefix, ward.bed_label_next, ward.bed_label_padding or 0
        )
        existing = (
            self.db.query(Bed.id)
            .filter(
                Bed.clinic_id == clinic_id,
                Bed.ward_id == ward_id,
                Bed.bed_label == label,
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
            bed_label=label,
            status=BedStatus.AVAILABLE,
            active=True,
        )
        self.db.add(bed)
        ward.bed_label_next = ward.bed_label_next + 1
        self.db.commit()
        self.db.refresh(bed)
        return WardAppendBedResponse(
            ward_id=ward.id,
            bed_id=bed.id,
            bed_label=bed.bed_label,
            next_number=ward.bed_label_next,
        )

    def retire_last_bed(
        self,
        *,
        clinic_id: UUID,
        ward_id: UUID,
        actor,
        reason: str,
    ) -> WardRetireBedResponse:
        ward = (
            self.db.query(Ward)
            .filter(Ward.id == ward_id)
            .with_for_update()
            .first()
        )
        if ward is None:
            raise HTTPException(status_code=404, detail="Ward not found")
        if ward.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not ward.bed_label_prefix or ward.bed_label_next is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ward is not configured for bed-range retirement",
            )

        candidate_number = ward.bed_label_next - 1
        if candidate_number < 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No generated beds available to retire",
            )
        label = self._format_label(
            ward.bed_label_prefix, candidate_number, ward.bed_label_padding or 0
        )
        bed = (
            self.db.query(Bed)
            .filter(
                Bed.clinic_id == clinic_id,
                Bed.ward_id == ward_id,
                Bed.bed_label == label,
            )
            .with_for_update()
            .first()
        )
        if bed is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Last generated bed not found",
            )
        if not bed.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Last generated bed is already retired",
            )

        retired = self.set_bed_active(
            clinic_id=clinic_id,
            bed_id=bed.id,
            active=False,
            actor=actor,
            reason=reason,
        )

        return WardRetireBedResponse(
            ward_id=ward.id,
            bed_id=retired.id,
            bed_label=retired.bed_label,
        )

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
            .with_for_update()
            .first()
        )
        if not ward:
            raise HTTPException(status_code=404, detail="Ward not found")
        if ward.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not ward.active:
            raise HTTPException(status_code=409, detail="Ward is inactive")

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

    def set_ward_active(
        self,
        *,
        clinic_id: UUID,
        ward_id: UUID,
        active: bool,
        actor,
        reason: str | None = None,
    ) -> Ward:
        ward = (
            self.db.query(Ward)
            .filter(Ward.id == ward_id)
            .with_for_update()
            .first()
        )
        if ward is None:
            raise HTTPException(status_code=404, detail="Ward not found")
        if ward.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")

        reason_text = reason.strip() if reason else None
        if not active and (reason_text is None or len(reason_text) < 3):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Reason must be at least 3 characters when deactivating ward",
            )

        if ward.active == active:
            self.event_service.build_event(
                event_type="WARD_ACTIVITY_CHANGED",
                actor_id=actor.id,
                actor_role=actor.role,
                clinic_id=clinic_id,
                patient_id=None,
                emitter="bed",
                payload={
                    "ward_id": str(ward.id),
                    "from_active": ward.active,
                    "to_active": active,
                    "reason": reason_text,
                    "no_op": True,
                },
            )
            self.db.commit()
            return ward

        if not active:
            occupied_bed = (
                self.db.query(BedAssignment.id)
                .join(
                    Bed,
                    and_(
                        Bed.id == BedAssignment.bed_id,
                        Bed.clinic_id == BedAssignment.clinic_id,
                    ),
                )
                .filter(
                    BedAssignment.clinic_id == clinic_id,
                    BedAssignment.released_at.is_(None),
                    Bed.ward_id == ward.id,
                )
                .with_for_update()
                .first()
            )
            if occupied_bed is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot deactivate ward while beds are occupied",
                )

        previous_active = ward.active
        ward.active = active
        self.event_service.build_event(
            event_type="WARD_ACTIVITY_CHANGED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=None,
            emitter="bed",
            payload={
                "ward_id": str(ward.id),
                "from_active": previous_active,
                "to_active": active,
                "reason": reason_text,
                "no_op": False,
            },
        )
        self.db.commit()
        self.db.refresh(ward)
        return ward

    def set_bed_active(
        self,
        *,
        clinic_id: UUID,
        bed_id: UUID,
        active: bool,
        actor,
        reason: str | None = None,
    ) -> Bed:
        bed = (
            self.db.query(Bed)
            .filter(Bed.id == bed_id)
            .with_for_update()
            .first()
        )
        if bed is None:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")

        reason_text = reason.strip() if reason else None
        if not active and (reason_text is None or len(reason_text) < 3):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Reason must be at least 3 characters when deactivating bed",
            )

        if bed.active == active:
            self.event_service.build_event(
                event_type="BED_ACTIVITY_CHANGED",
                actor_id=actor.id,
                actor_role=actor.role,
                clinic_id=clinic_id,
                patient_id=None,
                emitter="bed",
                payload={
                    "bed_id": str(bed.id),
                    "ward_id": str(bed.ward_id),
                    "from_active": bed.active,
                    "to_active": active,
                    "reason": reason_text,
                    "no_op": True,
                },
            )
            self.db.commit()
            return bed

        if not active:
            active_assignment = (
                self.db.query(BedAssignment.id)
                .filter(
                    BedAssignment.clinic_id == clinic_id,
                    BedAssignment.bed_id == bed.id,
                    BedAssignment.released_at.is_(None),
                )
                .with_for_update()
                .first()
            )
            if active_assignment is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot deactivate bed while occupied",
                )
        else:
            ward = (
                self.db.query(Ward)
                .filter(Ward.id == bed.ward_id)
                .with_for_update()
                .first()
            )
            if ward is None or ward.clinic_id != clinic_id:
                raise HTTPException(status_code=403, detail="Cross-clinic access denied")
            if not ward.active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot activate bed in inactive ward",
                )

        previous_active = bed.active
        bed.active = active
        self.event_service.build_event(
            event_type="BED_ACTIVITY_CHANGED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=None,
            emitter="bed",
            payload={
                "bed_id": str(bed.id),
                "ward_id": str(bed.ward_id),
                "from_active": previous_active,
                "to_active": active,
                "reason": reason_text,
                "no_op": False,
            },
        )
        self.db.commit()
        self.db.refresh(bed)
        return bed

    def update_bed_status(
        self,
        *,
        clinic_id: UUID,
        bed_id: UUID,
        status_value: BedStatus,
        actor,
        reason: str | None = None,
    ) -> Bed:
        bed = (
            self.db.query(Bed)
            .filter(Bed.id == bed_id)
            .with_for_update()
            .first()
        )
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not bed.active:
            raise HTTPException(status_code=409, detail="Bed is inactive")

        if bed.status == status_value:
            self.event_service.build_event(
                event_type="BED_STATUS_CHANGED",
                actor_id=actor.id,
                actor_role=actor.role,
                clinic_id=clinic_id,
                patient_id=None,
                emitter="bed",
                payload={
                    "bed_id": str(bed.id),
                    "ward_id": str(bed.ward_id),
                    "from_status": bed.status.value,
                    "to_status": status_value.value,
                    "reason": reason.strip() if reason else None,
                    "no_op": True,
                },
            )
            self.db.commit()
            return bed

        if status_value == BedStatus.OUT_OF_SERVICE:
            active_assignment = (
                self.db.query(BedAssignment.id)
                .filter(
                    BedAssignment.clinic_id == clinic_id,
                    BedAssignment.bed_id == bed.id,
                    BedAssignment.released_at.is_(None),
                )
                .with_for_update()
                .first()
            )
            if active_assignment:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot mark bed out of service while occupied",
                )
            if reason is None or len(reason.strip()) < 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Reason must be at least 3 characters for OUT_OF_SERVICE",
                )

        previous_status = bed.status
        bed.status = status_value
        try:
            self.event_service.build_event(
                event_type="BED_STATUS_CHANGED",
                actor_id=actor.id,
                actor_role=actor.role,
                clinic_id=clinic_id,
                patient_id=None,
                emitter="bed",
                payload={
                    "bed_id": str(bed.id),
                    "ward_id": str(bed.ward_id),
                    "from_status": previous_status.value,
                    "to_status": status_value.value,
                    "reason": reason.strip() if reason else None,
                    "no_op": False,
                },
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to update bed status",
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
            .with_for_update()
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
            .with_for_update()
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
            .with_for_update()
            .first()
        )
        if not bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if bed.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not bed.active:
            raise HTTPException(status_code=409, detail="Bed is inactive")
        if bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=409, detail="Bed not available")
        ward = (
            self.db.query(Ward)
            .filter(Ward.id == bed.ward_id)
            .with_for_update()
            .first()
        )
        if not ward or ward.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not ward.active:
            raise HTTPException(status_code=409, detail="Bed ward is inactive")

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
            self.event_service.build_event(
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
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bed already assigned",
            )
        self.db.refresh(assignment)
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
            .with_for_update()
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
            .with_for_update()
            .first()
        )
        if not new_bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if new_bed.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not new_bed.active:
            raise HTTPException(status_code=409, detail="Bed is inactive")
        if new_bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=409, detail="Bed not available")
        target_ward = (
            self.db.query(Ward)
            .filter(Ward.id == new_bed.ward_id)
            .with_for_update()
            .first()
        )
        if not target_ward or target_ward.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if not target_ward.active:
            raise HTTPException(status_code=409, detail="Bed ward is inactive")

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
            .with_for_update()
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
            self.event_service.build_event(
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
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bed already assigned",
            )

        self.db.refresh(new_assignment)
        return new_assignment
