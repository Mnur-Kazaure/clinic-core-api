# app/services/admission_request_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.admission_request import AdmissionRequest
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.models.patient import Patient
from app.models.ward import Ward
from app.shared.enums import (
    AdmissionRequestStatus,
    AdmissionStatus,
    AdmissionType,
    BedStatus,
    UserRole,
)
from app.services.event_service import EventService


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


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
            .first()
        )
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pending admission request already exists for this patient",
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
        self.db.commit()
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
                    Bed.status == BedStatus.AVAILABLE,
                    Ward.active.is_(True),
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
            status_value = _enum_value(request.status)
            admission_status_value = _enum_value(admission_status)
            is_approved_active_admission = (
                status_value == AdmissionRequestStatus.APPROVED.value
                and request.admission_id is not None
                and admission_status_value == AdmissionStatus.ACTIVE.value
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
            action_blockers: list[str] = []
            if status_value == AdmissionRequestStatus.APPROVED.value:
                if request.admission_id is None:
                    action_blockers.append("ADMISSION_RECORD_UNAVAILABLE")
                elif admission_status_value != AdmissionStatus.ACTIVE.value:
                    action_blockers.append("ADMISSION_NOT_ACTIVE")
                else:
                    if not has_active_bed and not available_bed_exists:
                        action_blockers.append("NO_AVAILABLE_BEDS_ASSIGN")
                    if has_active_bed and not available_bed_exists:
                        action_blockers.append("NO_AVAILABLE_BEDS_REASSIGN")

            setattr(request, "can_assign_bed", can_assign_bed)
            setattr(request, "can_reassign_bed", can_reassign_bed)
            setattr(request, "can_reassign_owner", False)
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
        self.db.flush()

        request.status = AdmissionRequestStatus.APPROVED
        request.admission_id = admission.id
        request.decided_by = actor.id
        request.decided_at = datetime.now(timezone.utc)
        request.decision_reason = decision_reason

        self.db.commit()
        self.db.refresh(request)
        self.db.refresh(admission)

        self.event_service.emit(
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
        self.db.commit()
        self.db.refresh(request)
        return request
