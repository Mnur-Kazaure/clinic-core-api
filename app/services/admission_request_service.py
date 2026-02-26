# app/services/admission_request_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.admission_request import AdmissionRequest
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.models.admission_visit_link import AdmissionVisitLink
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.user import User
from app.models.visit import Visit
from app.models.ward import Ward
from app.shared.enums import (
    AdmissionRequestStatus,
    AdmissionStatus,
    AdmissionType,
    BedStatus,
    MRNStatus,
    UserRole,
    VisitStatus,
)
from app.services.event_service import EventService


class AdmissionRequestService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    def create_request(
        self,
        *,
        patient_id: UUID,
        admission_type: AdmissionType,
        reason: str,
        actor,
    ) -> AdmissionRequest:
        patient = (
            self.db.query(Patient)
            .filter(Patient.id == patient_id)
            .with_for_update()
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if patient.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")

        existing_admission = (
            self.db.query(Admission)
            .filter(
                Admission.patient_id == patient_id,
                Admission.clinic_id == actor.clinic_id,
                Admission.status == AdmissionStatus.ACTIVE,
            )
            .with_for_update()
            .first()
        )
        if existing_admission:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active admission already exists for this patient",
            )

        existing_request = (
            self.db.query(AdmissionRequest)
            .filter(
                AdmissionRequest.patient_id == patient_id,
                AdmissionRequest.clinic_id == actor.clinic_id,
                AdmissionRequest.status == AdmissionRequestStatus.PENDING,
            )
            .with_for_update()
            .first()
        )
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pending admission request already exists for this patient",
            )
        if actor.role == UserRole.DOCTOR:
            self._ensure_doctor_has_active_assigned_visit(
                clinic_id=actor.clinic_id,
                patient_id=patient_id,
                actor_id=actor.id,
            )

        request = AdmissionRequest(
            clinic_id=actor.clinic_id,
            patient_id=patient_id,
            admission_type=admission_type,
            status=AdmissionRequestStatus.PENDING,
            reason=reason,
            requested_by=actor.id,
            requested_at=datetime.now(timezone.utc),
        )
        self.db.add(request)
        self.db.flush()
        self.event_service.build_event(
            event_type="ADMISSION_REQUEST_CREATED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=actor.clinic_id,
            patient_id=patient_id,
            emitter="admission",
            payload={
                "admission_request_id": str(request.id),
                "admission_type": admission_type.value,
                "status": request.status.value,
                "requested_at": request.requested_at.isoformat(),
            },
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pending admission request already exists for this patient",
            )
        self.db.refresh(request)
        return request

    def list_requests(
        self,
        *,
        actor,
        status: AdmissionRequestStatus | None = None,
    ) -> list[AdmissionRequest]:
        query = (
            self.db.query(AdmissionRequest)
            .filter(AdmissionRequest.clinic_id == actor.clinic_id)
        )
        if status:
            query = query.filter(AdmissionRequest.status == status)
        if actor.role not in {UserRole.ADMIN, UserRole.CLINIC_ADMIN}:
            query = query.filter(AdmissionRequest.requested_by == actor.id)
        requests = query.order_by(AdmissionRequest.requested_at.desc()).all()

        admission_ids = [request.admission_id for request in requests if request.admission_id]
        active_bed_map: dict[UUID, tuple[UUID, str]] = {}
        admission_status_map: dict[UUID, AdmissionStatus] = {}
        bed_timeline_map: dict[UUID, list[dict]] = {}
        active_visit_map: dict[UUID, dict] = {}
        if admission_ids:
            admissions = (
                self.db.query(Admission.id, Admission.status)
                .filter(
                    Admission.clinic_id == actor.clinic_id,
                    Admission.id.in_(admission_ids),
                )
                .all()
            )
            admission_status_map = {
                row.id: row.status
                for row in admissions
            }

            active_beds = (
                self.db.query(
                    BedAssignment.admission_id,
                    BedAssignment.bed_id,
                    Bed.bed_label,
                )
                .join(Bed, Bed.id == BedAssignment.bed_id)
                .filter(
                    BedAssignment.clinic_id == actor.clinic_id,
                    BedAssignment.released_at.is_(None),
                    BedAssignment.admission_id.in_(admission_ids),
                )
                .all()
            )
            active_bed_map = {
                row.admission_id: (row.bed_id, row.bed_label)
                for row in active_beds
            }

            active_visit_rows = (
                self.db.query(
                    AdmissionVisitLink.admission_id.label("admission_id"),
                    AdmissionVisitLink.linked_at.label("linked_at"),
                    Visit.id.label("visit_id"),
                    Visit.status.label("visit_status"),
                    Visit.service_line.label("visit_service_line"),
                    Visit.assigned_doctor_id.label("visit_owner_id"),
                    Visit.version.label("visit_version"),
                    User.full_name.label("visit_owner_name"),
                )
                .join(
                    Visit,
                    (Visit.id == AdmissionVisitLink.visit_id)
                    & (Visit.clinic_id == AdmissionVisitLink.clinic_id),
                )
                .outerjoin(User, User.id == Visit.assigned_doctor_id)
                .filter(
                    AdmissionVisitLink.clinic_id == actor.clinic_id,
                    AdmissionVisitLink.admission_id.in_(admission_ids),
                    Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
                )
                .order_by(
                    AdmissionVisitLink.admission_id.asc(),
                    AdmissionVisitLink.linked_at.desc(),
                    Visit.started_at.desc(),
                    Visit.created_at.desc(),
                    Visit.id.desc(),
                )
                .all()
            )
            for row in active_visit_rows:
                if row.admission_id in active_visit_map:
                    continue
                active_visit_map[row.admission_id] = {
                    "active_visit_id": row.visit_id,
                    "active_visit_status": row.visit_status,
                    "active_visit_service_line": row.visit_service_line,
                    "active_visit_owner_id": row.visit_owner_id,
                    "active_visit_owner_name": row.visit_owner_name,
                    "active_visit_version": row.visit_version,
                }

            timeline_rows = (
                self.db.query(
                    BedAssignment.id.label("assignment_id"),
                    BedAssignment.admission_id.label("admission_id"),
                    BedAssignment.assignment_type.label("assignment_type"),
                    BedAssignment.reason.label("reason"),
                    BedAssignment.assigned_at.label("assigned_at"),
                    BedAssignment.released_at.label("released_at"),
                    BedAssignment.assigned_by.label("assigned_by"),
                    User.full_name.label("assigned_by_name"),
                    Bed.id.label("bed_id"),
                    Bed.bed_label.label("bed_label"),
                    Ward.id.label("ward_id"),
                    Ward.name.label("ward_name"),
                )
                .join(
                    Bed,
                    (Bed.id == BedAssignment.bed_id)
                    & (Bed.clinic_id == BedAssignment.clinic_id),
                )
                .join(
                    Ward,
                    (Ward.id == Bed.ward_id)
                    & (Ward.clinic_id == Bed.clinic_id),
                )
                .outerjoin(User, User.id == BedAssignment.assigned_by)
                .filter(
                    BedAssignment.clinic_id == actor.clinic_id,
                    BedAssignment.admission_id.in_(admission_ids),
                )
                .order_by(
                    BedAssignment.admission_id.asc(),
                    BedAssignment.assigned_at.asc(),
                    BedAssignment.id.asc(),
                )
                .all()
            )

            timeline_by_admission: dict[UUID, list] = {}
            for row in timeline_rows:
                timeline_by_admission.setdefault(row.admission_id, []).append(row)

            for admission_id, rows in timeline_by_admission.items():
                timeline_items: list[dict] = []
                previous_bed_label: str | None = None
                for row in rows:
                    from_bed_label = (
                        previous_bed_label
                        if row.assignment_type.value == "TRANSFER"
                        else None
                    )
                    timeline_items.append(
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
                            "from_bed_label": from_bed_label,
                        }
                    )
                    previous_bed_label = row.bed_label
                bed_timeline_map[admission_id] = list(reversed(timeline_items))

        patient_ids = {request.patient_id for request in requests}
        patient_name_map: dict[UUID, str | None] = {}
        mrn_map: dict[UUID, str] = {}
        if patient_ids:
            patients = (
                self.db.query(Patient.id, Patient.full_name)
                .filter(
                    Patient.id.in_(patient_ids),
                    Patient.clinic_id == actor.clinic_id,
                )
                .all()
            )
            patient_name_map = {
                row.id: row.full_name
                for row in patients
            }
            mrns = (
                self.db.query(PatientMRN.patient_id, PatientMRN.mrn)
                .filter(
                    PatientMRN.patient_id.in_(patient_ids),
                    PatientMRN.clinic_id == actor.clinic_id,
                    PatientMRN.status == MRNStatus.ACTIVE,
                )
                .all()
            )
            mrn_map = {
                row.patient_id: row.mrn
                for row in mrns
            }

        available_bed_exists = False
        if requests:
            available_bed_exists = (
                self.db.query(Bed.id)
                .join(
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
                        BedAssignment.clinic_id == Bed.clinic_id,
                        BedAssignment.released_at.is_(None),
                    ),
                )
                .filter(
                    Bed.clinic_id == actor.clinic_id,
                    Bed.active.is_(True),
                    Ward.active.is_(True),
                    Bed.status == BedStatus.AVAILABLE,
                    BedAssignment.id.is_(None),
                )
                .first()
                is not None
            )

        for request in requests:
            bed_state = (
                active_bed_map.get(request.admission_id)
                if request.admission_id is not None
                else None
            )
            admission_status = (
                admission_status_map.get(request.admission_id)
                if request.admission_id is not None
                else None
            )
            setattr(request, "admission_status", admission_status)
            setattr(request, "has_active_bed_assignment", bed_state is not None)
            setattr(request, "current_bed_id", bed_state[0] if bed_state else None)
            setattr(request, "current_bed_label", bed_state[1] if bed_state else None)
            setattr(request, "patient_name", patient_name_map.get(request.patient_id))
            setattr(request, "patient_mrn", mrn_map.get(request.patient_id))
            setattr(request, "bed_timeline", bed_timeline_map.get(request.admission_id, []))
            visit_state = (
                active_visit_map.get(request.admission_id)
                if request.admission_id is not None
                else None
            )
            if visit_state:
                setattr(request, "active_visit_id", visit_state["active_visit_id"])
                setattr(request, "active_visit_status", visit_state["active_visit_status"])
                setattr(
                    request,
                    "active_visit_service_line",
                    visit_state["active_visit_service_line"],
                )
                setattr(
                    request,
                    "active_visit_owner_id",
                    visit_state["active_visit_owner_id"],
                )
                setattr(
                    request,
                    "active_visit_owner_name",
                    visit_state["active_visit_owner_name"],
                )
                setattr(
                    request,
                    "active_visit_version",
                    visit_state["active_visit_version"],
                )
            else:
                setattr(request, "active_visit_id", None)
                setattr(request, "active_visit_status", None)
                setattr(request, "active_visit_service_line", None)
                setattr(request, "active_visit_owner_id", None)
                setattr(request, "active_visit_owner_name", None)
                setattr(request, "active_visit_version", None)

            is_approved_active_admission = (
                request.status == AdmissionRequestStatus.APPROVED
                and request.admission_id is not None
                and admission_status == AdmissionStatus.ACTIVE
            )
            has_active_bed = bed_state is not None
            can_assign_bed = (
                is_approved_active_admission
                and not has_active_bed
                and available_bed_exists
            )
            can_reassign_bed = (
                is_approved_active_admission
                and has_active_bed
                and available_bed_exists
            )
            can_reassign_owner = (
                is_approved_active_admission
                and visit_state is not None
            )
            action_blockers: list[str] = []
            if request.status == AdmissionRequestStatus.APPROVED:
                if request.admission_id is None:
                    action_blockers.append("ADMISSION_RECORD_UNAVAILABLE")
                elif admission_status != AdmissionStatus.ACTIVE:
                    action_blockers.append("ADMISSION_NOT_ACTIVE")
                else:
                    if not has_active_bed and not available_bed_exists:
                        action_blockers.append("NO_AVAILABLE_BEDS_ASSIGN")
                    if has_active_bed and not available_bed_exists:
                        action_blockers.append("NO_AVAILABLE_BEDS_REASSIGN")
                    if visit_state is None:
                        action_blockers.append("NO_ACTIVE_VISIT_CONTEXT")

            setattr(request, "can_assign_bed", can_assign_bed)
            setattr(request, "can_reassign_bed", can_reassign_bed)
            setattr(request, "can_reassign_owner", can_reassign_owner)
            setattr(request, "action_blockers", action_blockers)

        return requests

    def approve_request(
        self,
        *,
        request_id: UUID,
        actor,
        decision_reason: str,
    ) -> tuple[AdmissionRequest, Admission]:
        request = (
            self.db.query(AdmissionRequest)
            .filter(AdmissionRequest.id == request_id)
            .with_for_update()
            .first()
        )
        if not request:
            raise HTTPException(status_code=404, detail="Admission request not found")
        if request.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if request.status != AdmissionRequestStatus.PENDING:
            raise HTTPException(status_code=409, detail="Admission request not pending")
        if actor.role not in {UserRole.ADMIN, UserRole.CLINIC_ADMIN}:
            raise HTTPException(status_code=403, detail="Admission approval access denied")

        existing_admission = (
            self.db.query(Admission)
            .filter(
                Admission.patient_id == request.patient_id,
                Admission.clinic_id == actor.clinic_id,
                Admission.status == AdmissionStatus.ACTIVE,
            )
            .with_for_update()
            .first()
        )
        if existing_admission:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active admission already exists for this patient",
            )

        admission = Admission(
            clinic_id=actor.clinic_id,
            patient_id=request.patient_id,
            admission_type=request.admission_type,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        self.db.add(admission)
        try:
            self.db.flush()

            active_visit = (
                self.db.query(Visit)
                .filter(
                    Visit.clinic_id == actor.clinic_id,
                    Visit.patient_id == request.patient_id,
                    Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
                )
                .order_by(Visit.started_at.desc(), Visit.created_at.desc())
                .with_for_update()
                .first()
            )
            if active_visit:
                existing_link = (
                    self.db.query(AdmissionVisitLink.id)
                    .filter(
                        AdmissionVisitLink.clinic_id == actor.clinic_id,
                        AdmissionVisitLink.visit_id == active_visit.id,
                    )
                    .first()
                )
                if existing_link is None:
                    self.db.add(
                        AdmissionVisitLink(
                            clinic_id=actor.clinic_id,
                            admission_id=admission.id,
                            visit_id=active_visit.id,
                            linked_at=datetime.now(timezone.utc),
                        )
                    )

            request.status = AdmissionRequestStatus.APPROVED
            request.admission_id = admission.id
            request.decided_by = actor.id
            request.decided_at = datetime.now(timezone.utc)
            request.decision_reason = decision_reason

            self.event_service.build_event(
                event_type="ADMISSION_REQUEST_APPROVED",
                actor_id=actor.id,
                actor_role=actor.role,
                clinic_id=actor.clinic_id,
                patient_id=admission.patient_id,
                emitter="admission",
                payload={
                    "admission_request_id": str(request.id),
                    "admission_id": str(admission.id),
                    "decision_reason": decision_reason,
                },
            )
            self.event_service.build_event(
                event_type="PATIENT_ADMITTED",
                actor_id=actor.id,
                actor_role=actor.role,
                clinic_id=actor.clinic_id,
                patient_id=admission.patient_id,
                emitter="admission",
                payload={
                    "admission_id": str(admission.id),
                    "admission_type": admission.admission_type.value,
                    "status": admission.status.value,
                    "admitted_at": admission.admitted_at.isoformat(),
                },
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active admission already exists for this patient",
            )
        self.db.refresh(request)
        self.db.refresh(admission)
        return request, admission

    def reject_request(
        self,
        *,
        request_id: UUID,
        actor,
        decision_reason: str,
    ) -> AdmissionRequest:
        request = (
            self.db.query(AdmissionRequest)
            .filter(AdmissionRequest.id == request_id)
            .with_for_update()
            .first()
        )
        if not request:
            raise HTTPException(status_code=404, detail="Admission request not found")
        if request.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if request.status != AdmissionRequestStatus.PENDING:
            raise HTTPException(status_code=409, detail="Admission request not pending")
        if actor.role not in {UserRole.ADMIN, UserRole.CLINIC_ADMIN}:
            raise HTTPException(status_code=403, detail="Admission approval access denied")

        request.status = AdmissionRequestStatus.REJECTED
        request.decided_by = actor.id
        request.decided_at = datetime.now(timezone.utc)
        request.decision_reason = decision_reason
        self.event_service.build_event(
            event_type="ADMISSION_REQUEST_REJECTED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=actor.clinic_id,
            patient_id=request.patient_id,
            emitter="admission",
            payload={
                "admission_request_id": str(request.id),
                "decision_reason": decision_reason,
            },
        )
        self.db.commit()
        self.db.refresh(request)
        return request

    def cancel_request(
        self,
        *,
        request_id: UUID,
        actor,
        reason: str,
    ) -> AdmissionRequest:
        request = (
            self.db.query(AdmissionRequest)
            .filter(AdmissionRequest.id == request_id)
            .with_for_update()
            .first()
        )
        if not request:
            raise HTTPException(status_code=404, detail="Admission request not found")
        if request.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if request.status != AdmissionRequestStatus.PENDING:
            raise HTTPException(status_code=409, detail="Admission request not pending")
        if request.requested_by != actor.id:
            raise HTTPException(status_code=403, detail="Only the requester can cancel")

        request.status = AdmissionRequestStatus.CANCELLED
        request.decided_by = actor.id
        request.decided_at = datetime.now(timezone.utc)
        request.decision_reason = reason
        self.event_service.build_event(
            event_type="ADMISSION_REQUEST_CANCELLED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=actor.clinic_id,
            patient_id=request.patient_id,
            emitter="admission",
            payload={
                "admission_request_id": str(request.id),
                "decision_reason": reason,
            },
        )
        self.db.commit()
        self.db.refresh(request)
        return request

    def _ensure_doctor_has_active_assigned_visit(
        self,
        *,
        clinic_id: UUID,
        patient_id: UUID,
        actor_id: UUID,
    ) -> None:
        active_assigned_visit = (
            self.db.query(Visit.id)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.patient_id == patient_id,
                Visit.assigned_doctor_id == actor_id,
                Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
            )
            .first()
        )
        if active_assigned_visit is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor can request admission only for assigned active visits",
            )
