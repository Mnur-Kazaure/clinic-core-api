from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.follow_up import FollowUp
from app.models.follow_up_status_history import FollowUpStatusHistory
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.user import User
from app.models.visit import Visit
from app.services.access_log_service import AccessLogService
from app.shared.enums import (
    FollowUpGeneratedBy,
    FollowUpStatus,
    FollowUpType,
    MRNStatus,
    PurposeOfUse,
    UserRole,
    VisitServiceLine,
    VisitStatus,
)


def _role_value(role) -> str:
    return getattr(role, "value", role)


def _to_service_line(owner_role: str) -> VisitServiceLine:
    if owner_role == UserRole.CHEW.value:
        return VisitServiceLine.ANC
    if owner_role == UserRole.MIDWIFE.value:
        return VisitServiceLine.MATERNITY
    return VisitServiceLine.OPD


class FollowUpWorkflowService:
    def __init__(self, db: Session):
        self.db = db
        self.access_log_service = AccessLogService(db)

    def list_clinician_follow_ups(
        self,
        *,
        clinic_id: UUID,
        actor,
        purpose_of_use,
        justification: str,
        now: datetime | None = None,
    ) -> dict:
        role = _role_value(actor.role)
        if role not in {
            UserRole.DOCTOR.value,
            UserRole.CHEW.value,
            UserRole.MIDWIFE.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinical follow-up access required",
            )

        effective_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        rows = (
            self.db.query(
                FollowUp,
                Patient.full_name.label("patient_name"),
                PatientMRN.mrn.label("patient_mrn"),
            )
            .join(
                Patient,
                (Patient.id == FollowUp.patient_id_canonical)
                & (Patient.clinic_id == FollowUp.clinic_id),
            )
            .outerjoin(
                PatientMRN,
                (PatientMRN.patient_id == FollowUp.patient_id_canonical)
                & (PatientMRN.clinic_id == FollowUp.clinic_id)
                & (PatientMRN.status == MRNStatus.ACTIVE),
            )
            .filter(
                FollowUp.clinic_id == clinic_id,
                FollowUp.owner_user_id == actor.id,
                FollowUp.status.in_([FollowUpStatus.SCHEDULED, FollowUpStatus.MISSED]),
            )
            .order_by(FollowUp.due_at.asc(), FollowUp.id.asc())
            .all()
        )
        active_visits = self._active_visit_map(
            clinic_id=clinic_id,
            owner_user_id=actor.id,
        )

        grouped = {"overdue": [], "today": [], "upcoming": []}
        today = effective_now.date()
        for row in rows:
            follow_up = row.FollowUp
            due_date = follow_up.due_at.date()
            item = self._serialize_follow_up_item(
                follow_up=follow_up,
                patient_name=row.patient_name,
                patient_mrn=row.patient_mrn,
                active_visit_id=active_visits.get(follow_up.patient_id_canonical),
            )
            if follow_up.status == FollowUpStatus.MISSED or due_date < today:
                grouped["overdue"].append(item)
            elif due_date == today:
                grouped["today"].append(item)
            else:
                grouped["upcoming"].append(item)

        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="FOLLOW_UP",
            action="READ",
            extra_payload={
                "scope": "CLINICIAN_DASHBOARD",
                "owner_user_id": str(actor.id),
            },
        )
        return grouped

    def list_reception_follow_ups(
        self,
        *,
        clinic_id: UUID,
        actor,
        purpose_of_use,
        justification: str,
        now: datetime | None = None,
    ) -> dict:
        role = _role_value(actor.role)
        if role not in {
            UserRole.RECEPTION.value,
            UserRole.CLINIC_ADMIN.value,
            UserRole.ADMIN.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reception follow-up access required",
            )

        effective_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        start_of_today = datetime.combine(
            effective_now.date(),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        end_of_tomorrow = start_of_today + timedelta(days=2)
        rows = (
            self.db.query(
                FollowUp,
                Patient.full_name.label("patient_name"),
                PatientMRN.mrn.label("patient_mrn"),
                User.role.label("owner_role"),
                User.full_name.label("owner_name"),
            )
            .join(
                Patient,
                (Patient.id == FollowUp.patient_id_canonical)
                & (Patient.clinic_id == FollowUp.clinic_id),
            )
            .join(User, User.id == FollowUp.owner_user_id)
            .outerjoin(
                PatientMRN,
                (PatientMRN.patient_id == FollowUp.patient_id_canonical)
                & (PatientMRN.clinic_id == FollowUp.clinic_id)
                & (PatientMRN.status == MRNStatus.ACTIVE),
            )
            .filter(
                FollowUp.clinic_id == clinic_id,
                FollowUp.status.in_([FollowUpStatus.SCHEDULED, FollowUpStatus.MISSED]),
                FollowUp.due_at < end_of_tomorrow,
            )
            .order_by(FollowUp.due_at.asc(), FollowUp.id.asc())
            .all()
        )

        grouped = {"today": [], "tomorrow": []}
        today = effective_now.date()
        tomorrow = today + timedelta(days=1)
        for row in rows:
            follow_up = row.FollowUp
            due_date = follow_up.due_at.date()
            item = self._serialize_follow_up_item(
                follow_up=follow_up,
                patient_name=row.patient_name,
                patient_mrn=row.patient_mrn,
                active_visit_id=None,
                owner_role=_role_value(row.owner_role),
                owner_name=row.owner_name,
            )
            if follow_up.status == FollowUpStatus.MISSED or due_date <= today:
                grouped["today"].append(item)
            elif due_date == tomorrow:
                grouped["tomorrow"].append(item)

        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="FOLLOW_UP",
            action="READ",
            extra_payload={"scope": "RECEPTION_DASHBOARD"},
        )
        return grouped

    def reschedule_follow_up(
        self,
        *,
        clinic_id: UUID,
        follow_up_id: UUID,
        actor,
        due_at: datetime,
        reason: str,
        justification: str,
    ) -> FollowUp:
        role = _role_value(actor.role)
        if role not in {
            UserRole.RECEPTION.value,
            UserRole.CLINIC_ADMIN.value,
            UserRole.ADMIN.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reschedule access denied",
            )

        original = (
            self.db.query(FollowUp)
            .filter(
                FollowUp.id == follow_up_id,
                FollowUp.clinic_id == clinic_id,
            )
            .with_for_update()
            .first()
        )
        if original is None:
            raise HTTPException(status_code=404, detail="Follow-up not found")
        if original.status not in {FollowUpStatus.SCHEDULED, FollowUpStatus.MISSED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only scheduled or missed follow-ups can be rescheduled",
            )

        old_status = original.status
        original.status = FollowUpStatus.CANCELLED
        original.cancel_reason_code = "RESCHEDULED"
        original.cancel_reason_text = reason.strip()
        self.db.add(
            FollowUpStatusHistory(
                follow_up_id=original.id,
                old_status=old_status,
                new_status=FollowUpStatus.CANCELLED,
                actor_user_id=actor.id,
                reason="RESCHEDULED",
                changed_at=datetime.now(timezone.utc),
            )
        )

        replacement = FollowUp(
            clinic_id=original.clinic_id,
            patient_id_canonical=original.patient_id_canonical,
            type=original.type,
            priority=original.priority,
            status=FollowUpStatus.SCHEDULED,
            due_at=due_at.astimezone(timezone.utc),
            owner_user_id=original.owner_user_id,
            reason=original.reason,
            origin_visit_id=original.origin_visit_id,
            origin_admission_id=original.origin_admission_id,
            chronic_recall_id=original.chronic_recall_id,
            generated_by=FollowUpGeneratedBy.USER,
            created_by=actor.id,
            rescheduled_from_id=original.id,
        )
        self.db.add(replacement)
        self.db.commit()
        self.db.refresh(replacement)

        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=replacement.patient_id_canonical,
            purpose_of_use=PurposeOfUse.OPERATIONS,
            justification=justification,
            resource="FOLLOW_UP",
            action="WRITE",
            extra_payload={
                "operation": "RESCHEDULE",
                "original_follow_up_id": str(original.id),
                "replacement_follow_up_id": str(replacement.id),
            },
        )
        return replacement

    def get_follow_up_item_by_id(
        self,
        *,
        clinic_id: UUID,
        follow_up_id: UUID,
    ) -> dict:
        row = (
            self.db.query(
                FollowUp,
                Patient.full_name.label("patient_name"),
                PatientMRN.mrn.label("patient_mrn"),
                User.role.label("owner_role"),
                User.full_name.label("owner_name"),
            )
            .join(
                Patient,
                (Patient.id == FollowUp.patient_id_canonical)
                & (Patient.clinic_id == FollowUp.clinic_id),
            )
            .join(User, User.id == FollowUp.owner_user_id)
            .outerjoin(
                PatientMRN,
                (PatientMRN.patient_id == FollowUp.patient_id_canonical)
                & (PatientMRN.clinic_id == FollowUp.clinic_id)
                & (PatientMRN.status == MRNStatus.ACTIVE),
            )
            .filter(
                FollowUp.id == follow_up_id,
                FollowUp.clinic_id == clinic_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Follow-up not found")
        return self._serialize_follow_up_item(
            follow_up=row.FollowUp,
            patient_name=row.patient_name,
            patient_mrn=row.patient_mrn,
            owner_role=_role_value(row.owner_role),
            owner_name=row.owner_name,
            active_visit_id=None,
        )

    def complete_linked_follow_up_on_visit_sign(
        self,
        *,
        clinic_id: UUID,
        actor_id: UUID,
        visit_id: UUID,
        patient_id_canonical: UUID,
        linked_follow_up_id: UUID | None,
        signed_at: datetime,
        commit: bool = False,
    ) -> FollowUp | None:
        if linked_follow_up_id is None:
            return None

        follow_up = (
            self.db.query(FollowUp)
            .filter(
                FollowUp.id == linked_follow_up_id,
                FollowUp.clinic_id == clinic_id,
            )
            .with_for_update()
            .first()
        )
        if follow_up is None:
            raise HTTPException(status_code=404, detail="Linked follow-up not found")
        if follow_up.patient_id_canonical != patient_id_canonical:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Linked follow-up patient mismatch",
            )
        if follow_up.status not in {FollowUpStatus.SCHEDULED, FollowUpStatus.MISSED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Linked follow-up is not actionable",
            )

        old_status = follow_up.status
        follow_up.status = FollowUpStatus.COMPLETED
        follow_up.completed_visit_id = visit_id
        follow_up.completed_at = signed_at
        self.db.add(
            FollowUpStatusHistory(
                follow_up_id=follow_up.id,
                old_status=old_status,
                new_status=FollowUpStatus.COMPLETED,
                actor_user_id=actor_id,
                reason="VISIT_SIGN_LINKED_COMPLETION",
                changed_at=signed_at,
            )
        )
        if commit:
            self.db.commit()
            self.db.refresh(follow_up)
        else:
            self.db.flush()
        return follow_up

    def _active_visit_map(self, *, clinic_id: UUID, owner_user_id: UUID) -> dict[UUID, UUID]:
        rows = (
            self.db.query(Visit.id, Visit.patient_id)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.assigned_doctor_id == owner_user_id,
                Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
            )
            .order_by(Visit.created_at.desc())
            .all()
        )
        result: dict[UUID, UUID] = {}
        for row in rows:
            if row.patient_id not in result:
                result[row.patient_id] = row.id
        return result

    def _serialize_follow_up_item(
        self,
        *,
        follow_up: FollowUp,
        patient_name: str | None,
        patient_mrn: str | None,
        active_visit_id: UUID | None,
        owner_role: str | None = None,
        owner_name: str | None = None,
    ) -> dict:
        role = owner_role or self._load_owner_role(follow_up.owner_user_id)
        return {
            "id": follow_up.id,
            "clinic_id": follow_up.clinic_id,
            "patient_id_canonical": follow_up.patient_id_canonical,
            "patient_name": patient_name,
            "patient_mrn": patient_mrn,
            "type": follow_up.type,
            "priority": follow_up.priority,
            "status": follow_up.status,
            "due_at": follow_up.due_at,
            "reason": follow_up.reason,
            "owner_user_id": follow_up.owner_user_id,
            "owner_user_name": owner_name,
            "owner_role": role,
            "recommended_service_line": _to_service_line(role),
            "active_visit_id": active_visit_id,
            "linked_visit_id": follow_up.origin_visit_id,
        }

    def _load_owner_role(self, owner_user_id: UUID) -> str:
        role = self.db.query(User.role).filter(User.id == owner_user_id).scalar()
        return _role_value(role) if role is not None else UserRole.DOCTOR.value
