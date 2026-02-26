from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.models.triage_assessment import TriageAssessment
from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.schemas.triage import (
    TriageDraftRequest,
    TriageFinalizeRequest,
    TriageSignRequest,
    TriageSupersedeRequest,
)
from app.services.event_service import EventService
from app.shared.enums import (
    ClinicalPriorityLevel,
    ClinicalPrioritySource,
    TriageAssessmentRecordStatus,
    TriageFallbackReasonCode,
    TriageFinalizeAction,
    TriageScaleVersion,
    UserRole,
    VisitServiceLine,
    VisitStatus,
    VisitTriageState,
)


SERVICE_LINE_TRIAGE_ROLES: dict[VisitServiceLine, set[UserRole]] = {
    VisitServiceLine.OPD: {UserRole.CHEW},
    VisitServiceLine.ANC: {UserRole.CHEW, UserRole.MIDWIFE},
    VisitServiceLine.MATERNITY: {UserRole.MIDWIFE},
}

TRIAGE_ROLE_SERVICE_LINES: dict[UserRole, set[VisitServiceLine]] = {
    UserRole.CHEW: {VisitServiceLine.OPD, VisitServiceLine.ANC},
    UserRole.MIDWIFE: {VisitServiceLine.ANC, VisitServiceLine.MATERNITY},
    UserRole.DOCTOR: {
        VisitServiceLine.OPD,
        VisitServiceLine.ANC,
        VisitServiceLine.MATERNITY,
    },
}

RESPIRATORY_SIGNAL_TOKENS = {
    "RESP",
    "BREATH",
    "OXYGEN",
    "SPO2",
    "ASTHMA",
}


class TriageService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    def upsert_draft_assessment(
        self,
        *,
        visit_id: UUID,
        payload: TriageDraftRequest,
        current_user,
        idempotency_key: str | None = None,
    ) -> tuple[TriageAssessment, Visit]:
        visit = self._load_locked_visit(visit_id=visit_id, current_user=current_user)
        self._ensure_expected_version(visit=visit, expected_version=payload.expected_version)

        if visit.status not in {VisitStatus.REGISTERED, VisitStatus.TRIAGED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_INVALID_VISIT_STATE", "visit_status": visit.status.value},
            )

        self._ensure_triage_authority(
            user=current_user,
            service_line=visit.service_line,
            is_doctor_fallback=payload.is_doctor_fallback,
        )
        self._validate_payload(payload=payload)

        now = datetime.now(timezone.utc)
        active = self._active_assessment(visit_id=visit.id)
        if active and active.record_status == TriageAssessmentRecordStatus.SIGNED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_ALREADY_SIGNED", "triage_assessment_id": str(active.id)},
            )

        if active:
            triage = active
            triage.assessed_by = current_user.id
            triage.assessed_by_role = self._role_value(current_user.role)
            triage.assessed_at = now
            triage.finalized_by = current_user.id
            triage.finalized_at = now
            triage.triage_scale_version = TriageScaleVersion.PHC_V1
            triage.acuity_level = payload.acuity_level
            triage.chief_complaint = payload.chief_complaint.strip()
            triage.complaint_severity = payload.complaint_severity
            triage.triage_note = (payload.triage_note or "").strip() or None
            triage.danger_sign_codes = payload.danger_sign_codes or []
            triage.temp_c = payload.temp_c
            triage.pulse_bpm = payload.pulse_bpm
            triage.rr_bpm = payload.rr_bpm
            triage.sbp_mmhg = payload.sbp_mmhg
            triage.dbp_mmhg = payload.dbp_mmhg
            triage.spo2_pct = payload.spo2_pct
            triage.missing_vitals_reason_code = payload.missing_vitals_reason_code
            triage.is_doctor_fallback = payload.is_doctor_fallback
            triage.fallback_reason_code = payload.fallback_reason_code
            triage.fallback_reason_text = (payload.fallback_reason_text or "").strip() or None
            triage.triage_finalize_action = payload.action
            triage.referred_facility = (payload.referred_facility or "").strip() or None
            triage.referral_reason = (payload.referral_reason or "").strip() or None
            triage.idempotency_key = idempotency_key
            triage.record_status = TriageAssessmentRecordStatus.DRAFT
        else:
            triage = TriageAssessment(
                clinic_id=visit.clinic_id,
                visit_id=visit.id,
                patient_id=visit.patient_id,
                assessed_by=current_user.id,
                assessed_by_role=self._role_value(current_user.role),
                assessed_at=now,
                record_status=TriageAssessmentRecordStatus.DRAFT,
                finalized_by=current_user.id,
                finalized_at=now,
                triage_scale_version=TriageScaleVersion.PHC_V1,
                acuity_level=payload.acuity_level,
                chief_complaint=payload.chief_complaint.strip(),
                complaint_severity=payload.complaint_severity,
                triage_note=(payload.triage_note or "").strip() or None,
                danger_sign_codes=payload.danger_sign_codes or [],
                temp_c=payload.temp_c,
                pulse_bpm=payload.pulse_bpm,
                rr_bpm=payload.rr_bpm,
                sbp_mmhg=payload.sbp_mmhg,
                dbp_mmhg=payload.dbp_mmhg,
                spo2_pct=payload.spo2_pct,
                missing_vitals_reason_code=payload.missing_vitals_reason_code,
                is_doctor_fallback=payload.is_doctor_fallback,
                fallback_reason_code=payload.fallback_reason_code,
                fallback_reason_text=(payload.fallback_reason_text or "").strip() or None,
                triage_finalize_action=payload.action,
                referred_facility=(payload.referred_facility or "").strip() or None,
                referral_reason=(payload.referral_reason or "").strip() or None,
                idempotency_key=idempotency_key,
            )
            self.db.add(triage)

        visit.triage_state = VisitTriageState.PENDING
        visit.version = (visit.version or 0) + 1
        self.db.add(visit)

        self.db.commit()
        self.db.refresh(triage)
        self.db.refresh(visit)

        self._emit_triage_drafted_event(
            triage=triage,
            current_user=current_user,
            visit=visit,
            idempotency_key=idempotency_key,
        )
        return triage, visit

    def sign_assessment(
        self,
        *,
        visit_id: UUID,
        payload: TriageSignRequest,
        current_user,
        idempotency_key: str | None = None,
    ) -> tuple[TriageAssessment, Visit]:
        visit = self._load_locked_visit(visit_id=visit_id, current_user=current_user)
        self._ensure_expected_version(visit=visit, expected_version=payload.expected_version)

        if visit.status not in {VisitStatus.REGISTERED, VisitStatus.TRIAGED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_INVALID_VISIT_STATE", "visit_status": visit.status.value},
            )

        active = self._active_assessment(visit_id=visit.id)
        if not active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_DRAFT_REQUIRED"},
            )

        self._ensure_triage_authority(
            user=current_user,
            service_line=visit.service_line,
            is_doctor_fallback=active.is_doctor_fallback,
        )

        if active.record_status == TriageAssessmentRecordStatus.SIGNED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_ALREADY_SIGNED", "triage_assessment_id": str(active.id)},
            )

        now = datetime.now(timezone.utc)
        previous_priority = self._latest_priority_level(visit_id=visit.id, clinic_id=visit.clinic_id)

        active.record_status = TriageAssessmentRecordStatus.SIGNED
        active.finalized_by = current_user.id
        active.finalized_at = now
        self.db.add(active)

        self.db.add(
            ClinicalPriorityEvent(
                clinic_id=visit.clinic_id,
                visit_id=visit.id,
                patient_id=visit.patient_id,
                level=active.acuity_level,
                source=ClinicalPrioritySource.TRIAGE,
                reason="triage_assessment_signed",
                set_by=current_user.id,
                set_at=now,
            )
        )

        original_status = visit.status
        target_status = self._resolve_target_status(action=active.triage_finalize_action)
        status_changed = original_status != target_status
        visit.status = target_status
        visit.completed_at = now if target_status == VisitStatus.COMPLETED else None
        visit.triage_state = VisitTriageState.TRIAGED
        visit.triage_acuity = active.acuity_level
        visit.triaged_at = now
        visit.triaged_by = current_user.id
        visit.version = (visit.version or 0) + 1
        self.db.add(visit)

        if status_changed:
            self.db.add(
                VisitStatusHistory(
                    visit_id=visit.id,
                    from_status=original_status,
                    to_status=target_status,
                    changed_by=current_user.id,
                    source="manual",
                    reason_code=(
                        "REFERRED_OUT_FROM_TRIAGE"
                        if active.triage_finalize_action == TriageFinalizeAction.REFER_OUT_IMMEDIATE
                        else None
                    ),
                    reason_text=(
                        active.referral_reason
                        if active.triage_finalize_action == TriageFinalizeAction.REFER_OUT_IMMEDIATE
                        else None
                    ),
                    idempotency_key=idempotency_key,
                )
            )

        self.db.commit()
        self.db.refresh(active)
        self.db.refresh(visit)

        self._emit_triage_signed_event(
            triage=active,
            current_user=current_user,
            visit=visit,
            idempotency_key=idempotency_key,
        )
        self._emit_priority_event_if_changed(
            previous=previous_priority,
            current=active.acuity_level,
            current_user=current_user,
            visit=visit,
            assessed_at=active.assessed_at,
        )
        if status_changed:
            self._emit_visit_status_event(
                visit=visit,
                current_user=current_user,
                from_status=original_status,
                to_status=target_status,
                triage_assessment_id=active.id,
                idempotency_key=idempotency_key,
            )
        return active, visit

    def finalize_assessment(
        self,
        *,
        visit_id: UUID,
        payload: TriageFinalizeRequest,
        current_user,
        idempotency_key: str | None = None,
    ) -> tuple[TriageAssessment, Visit]:
        visit = self._load_locked_visit(visit_id=visit_id, current_user=current_user)
        self._ensure_expected_version(visit=visit, expected_version=payload.expected_version)

        active = self._active_assessment(visit_id=visit.id)
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_ALREADY_EXISTS", "triage_assessment_id": str(active.id)},
            )

        if visit.status not in {VisitStatus.REGISTERED, VisitStatus.TRIAGED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_INVALID_VISIT_STATE", "visit_status": visit.status.value},
            )

        self._ensure_triage_authority(
            user=current_user,
            service_line=visit.service_line,
            is_doctor_fallback=payload.is_doctor_fallback,
        )
        self._validate_payload(payload=payload)

        now = datetime.now(timezone.utc)
        previous_priority = self._latest_priority_level(visit_id=visit.id, clinic_id=visit.clinic_id)

        triage = TriageAssessment(
            clinic_id=visit.clinic_id,
            visit_id=visit.id,
            patient_id=visit.patient_id,
            assessed_by=current_user.id,
            assessed_by_role=self._role_value(current_user.role),
            assessed_at=now,
            record_status=TriageAssessmentRecordStatus.SIGNED,
            finalized_by=current_user.id,
            finalized_at=now,
            triage_scale_version=TriageScaleVersion.PHC_V1,
            acuity_level=payload.acuity_level,
            chief_complaint=payload.chief_complaint.strip(),
            complaint_severity=payload.complaint_severity,
            triage_note=(payload.triage_note or "").strip() or None,
            danger_sign_codes=payload.danger_sign_codes or [],
            temp_c=payload.temp_c,
            pulse_bpm=payload.pulse_bpm,
            rr_bpm=payload.rr_bpm,
            sbp_mmhg=payload.sbp_mmhg,
            dbp_mmhg=payload.dbp_mmhg,
            spo2_pct=payload.spo2_pct,
            missing_vitals_reason_code=payload.missing_vitals_reason_code,
            is_doctor_fallback=payload.is_doctor_fallback,
            fallback_reason_code=payload.fallback_reason_code,
            fallback_reason_text=(payload.fallback_reason_text or "").strip() or None,
            triage_finalize_action=payload.action,
            referred_facility=(payload.referred_facility or "").strip() or None,
            referral_reason=(payload.referral_reason or "").strip() or None,
            idempotency_key=idempotency_key,
        )
        self.db.add(triage)

        self.db.add(
            ClinicalPriorityEvent(
                clinic_id=visit.clinic_id,
                visit_id=visit.id,
                patient_id=visit.patient_id,
                level=payload.acuity_level,
                source=ClinicalPrioritySource.TRIAGE,
                reason="triage_assessment_finalized",
                set_by=current_user.id,
                set_at=now,
            )
        )

        original_status = visit.status
        target_status = self._resolve_target_status(action=payload.action)
        status_changed = original_status != target_status
        if status_changed:
            visit.status = target_status
            visit.completed_at = now if target_status == VisitStatus.COMPLETED else None
            visit.triage_state = VisitTriageState.TRIAGED
            visit.triage_acuity = payload.acuity_level
            visit.triaged_at = now
            visit.triaged_by = current_user.id
            visit.version = (visit.version or 0) + 1
            self.db.add(visit)
            self.db.add(
                VisitStatusHistory(
                    visit_id=visit.id,
                    from_status=original_status,
                    to_status=target_status,
                    changed_by=current_user.id,
                    source="manual",
                    reason_code=(
                        "REFERRED_OUT_FROM_TRIAGE"
                        if payload.action == TriageFinalizeAction.REFER_OUT_IMMEDIATE
                        else None
                    ),
                    reason_text=(
                        triage.referral_reason
                        if payload.action == TriageFinalizeAction.REFER_OUT_IMMEDIATE
                        else None
                    ),
                    idempotency_key=idempotency_key,
                )
            )
        else:
            visit.triage_state = VisitTriageState.TRIAGED
            visit.triage_acuity = payload.acuity_level
            visit.triaged_at = now
            visit.triaged_by = current_user.id
            visit.version = (visit.version or 0) + 1
            self.db.add(visit)

        self.db.commit()
        self.db.refresh(triage)
        self.db.refresh(visit)

        self._emit_triage_finalized_event(
            triage=triage,
            current_user=current_user,
            visit=visit,
            idempotency_key=idempotency_key,
        )
        self._emit_priority_event_if_changed(
            previous=previous_priority,
            current=payload.acuity_level,
            current_user=current_user,
            visit=visit,
            assessed_at=triage.assessed_at,
        )
        if status_changed:
            self._emit_visit_status_event(
                visit=visit,
                current_user=current_user,
                from_status=original_status,
                to_status=target_status,
                triage_assessment_id=triage.id,
                idempotency_key=idempotency_key,
            )
        return triage, visit

    def supersede_assessment(
        self,
        *,
        visit_id: UUID,
        payload: TriageSupersedeRequest,
        current_user,
        idempotency_key: str | None = None,
    ) -> tuple[TriageAssessment, Visit]:
        visit = self._load_locked_visit(visit_id=visit_id, current_user=current_user)
        self._ensure_expected_version(visit=visit, expected_version=payload.expected_version)

        if visit.status not in {VisitStatus.REGISTERED, VisitStatus.TRIAGED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_SUPERSEDE_FORBIDDEN_AT_STATUS", "visit_status": visit.status.value},
            )

        active = self._active_assessment(visit_id=visit.id)
        if not active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_ACTIVE_RECORD_REQUIRED"},
            )

        self._ensure_triage_authority(
            user=current_user,
            service_line=visit.service_line,
            is_doctor_fallback=payload.is_doctor_fallback,
        )
        self._validate_payload(payload=payload)

        now = datetime.now(timezone.utc)
        previous_priority = self._latest_priority_level(visit_id=visit.id, clinic_id=visit.clinic_id)

        active.superseded_at = now
        self.db.add(active)

        replacement = TriageAssessment(
            clinic_id=visit.clinic_id,
            visit_id=visit.id,
            patient_id=visit.patient_id,
            assessed_by=current_user.id,
            assessed_by_role=self._role_value(current_user.role),
            assessed_at=now,
            record_status=TriageAssessmentRecordStatus.SIGNED,
            finalized_by=current_user.id,
            finalized_at=now,
            triage_scale_version=TriageScaleVersion.PHC_V1,
            acuity_level=payload.acuity_level,
            chief_complaint=payload.chief_complaint.strip(),
            complaint_severity=payload.complaint_severity,
            triage_note=(payload.triage_note or "").strip() or None,
            danger_sign_codes=payload.danger_sign_codes or [],
            temp_c=payload.temp_c,
            pulse_bpm=payload.pulse_bpm,
            rr_bpm=payload.rr_bpm,
            sbp_mmhg=payload.sbp_mmhg,
            dbp_mmhg=payload.dbp_mmhg,
            spo2_pct=payload.spo2_pct,
            missing_vitals_reason_code=payload.missing_vitals_reason_code,
            is_doctor_fallback=payload.is_doctor_fallback,
            fallback_reason_code=payload.fallback_reason_code,
            fallback_reason_text=(payload.fallback_reason_text or "").strip() or None,
            triage_finalize_action=payload.action,
            referred_facility=(payload.referred_facility or "").strip() or None,
            referral_reason=(payload.referral_reason or "").strip() or None,
            supersedes_assessment_id=active.id,
            correction_reason_code=payload.correction_reason_code.strip(),
            correction_reason_text=(payload.correction_reason_text or "").strip() or None,
            idempotency_key=idempotency_key,
        )
        self.db.add(replacement)

        self.db.add(
            ClinicalPriorityEvent(
                clinic_id=visit.clinic_id,
                visit_id=visit.id,
                patient_id=visit.patient_id,
                level=payload.acuity_level,
                source=ClinicalPrioritySource.TRIAGE,
                reason="triage_assessment_superseded",
                set_by=current_user.id,
                set_at=now,
            )
        )

        original_status = visit.status
        target_status = self._resolve_target_status(action=payload.action)
        status_changed = original_status != target_status
        visit.status = target_status
        visit.completed_at = now if target_status == VisitStatus.COMPLETED else None
        visit.triage_state = VisitTriageState.TRIAGED
        visit.triage_acuity = payload.acuity_level
        visit.triaged_at = now
        visit.triaged_by = current_user.id
        visit.version = (visit.version or 0) + 1
        self.db.add(visit)

        if status_changed:
            self.db.add(
                VisitStatusHistory(
                    visit_id=visit.id,
                    from_status=original_status,
                    to_status=target_status,
                    changed_by=current_user.id,
                    source="manual",
                    reason_code=(
                        "REFERRED_OUT_FROM_TRIAGE"
                        if payload.action == TriageFinalizeAction.REFER_OUT_IMMEDIATE
                        else None
                    ),
                    reason_text=(
                        replacement.referral_reason
                        if payload.action == TriageFinalizeAction.REFER_OUT_IMMEDIATE
                        else None
                    ),
                    idempotency_key=idempotency_key,
                )
            )

        self.db.commit()
        self.db.refresh(replacement)
        self.db.refresh(visit)

        self._emit_triage_superseded_event(
            previous=active,
            replacement=replacement,
            current_user=current_user,
            visit=visit,
            idempotency_key=idempotency_key,
        )
        self._emit_priority_event_if_changed(
            previous=previous_priority,
            current=payload.acuity_level,
            current_user=current_user,
            visit=visit,
            assessed_at=replacement.assessed_at,
        )
        if status_changed:
            self._emit_visit_status_event(
                visit=visit,
                current_user=current_user,
                from_status=original_status,
                to_status=target_status,
                triage_assessment_id=replacement.id,
                idempotency_key=idempotency_key,
            )
        return replacement, visit

    def get_active_assessment(self, *, visit_id: UUID, current_user) -> TriageAssessment | None:
        visit = (
            self.db.query(Visit)
            .filter(Visit.id == visit_id)
            .first()
        )
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visit not found",
            )
        if visit.clinic_id != current_user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )
        return self._active_assessment(visit_id=visit.id, signed_only=False)

    def list_triage_queue(
        self,
        *,
        current_user,
        triage_state: VisitTriageState | None = VisitTriageState.PENDING,
        limit: int = 150,
    ) -> list[Visit]:
        actor_role = self._role_enum(current_user.role)
        if actor_role is None:
            return []

        allowed_service_lines = TRIAGE_ROLE_SERVICE_LINES.get(actor_role, set())
        if not allowed_service_lines:
            return []

        query = (
            self.db.query(Visit)
            .filter(
                Visit.clinic_id == current_user.clinic_id,
                Visit.service_line.in_(list(allowed_service_lines)),
                Visit.status.in_([VisitStatus.REGISTERED, VisitStatus.TRIAGED]),
                Visit.triage_state.in_([VisitTriageState.PENDING, VisitTriageState.TRIAGED]),
            )
        )

        if triage_state is not None:
            query = query.filter(Visit.triage_state == triage_state)

        visits = query.all()
        ordered = self._order_triage_queue(visits)
        return ordered[:limit]

    def has_active_assessment(self, *, visit_id: UUID) -> bool:
        return self._active_assessment(visit_id=visit_id, signed_only=True) is not None

    def _active_assessment(
        self,
        *,
        visit_id: UUID,
        signed_only: bool = False,
    ) -> TriageAssessment | None:
        query = (
            self.db.query(TriageAssessment)
            .filter(
                TriageAssessment.visit_id == visit_id,
                TriageAssessment.superseded_at.is_(None),
            )
        )
        if signed_only:
            query = query.filter(
                TriageAssessment.record_status == TriageAssessmentRecordStatus.SIGNED
            )
        return query.order_by(TriageAssessment.created_at.desc()).first()

    def _order_triage_queue(self, visits: list[Visit]) -> list[Visit]:
        if not visits:
            return []

        triage_state_rank = {
            VisitTriageState.PENDING: 0,
            VisitTriageState.TRIAGED: 1,
            VisitTriageState.NOT_REQUIRED: 2,
        }
        acuity_rank = {
            ClinicalPriorityLevel.CRITICAL: 0,
            ClinicalPriorityLevel.URGENT: 1,
            ClinicalPriorityLevel.ROUTINE: 2,
        }

        def _as_aware(value: datetime | None) -> datetime:
            if value is None:
                return datetime.now(timezone.utc)
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        def _sort_key(visit: Visit):
            state = visit.triage_state or VisitTriageState.PENDING
            state_order = triage_state_rank.get(state, 3)

            if state == VisitTriageState.TRIAGED:
                acuity_order = acuity_rank.get(
                    visit.triage_acuity or ClinicalPriorityLevel.ROUTINE,
                    3,
                )
                ordering_time = _as_aware(visit.triaged_at or visit.started_at)
            else:
                acuity_order = 9
                ordering_time = _as_aware(visit.started_at)

            return (state_order, acuity_order, ordering_time, str(visit.id))

        return sorted(visits, key=_sort_key)

    def _role_enum(self, role) -> UserRole | None:
        if isinstance(role, UserRole):
            return role
        try:
            return UserRole(str(role))
        except ValueError:
            return None

    def _load_locked_visit(self, *, visit_id: UUID, current_user) -> Visit:
        visit = (
            self.db.query(Visit)
            .filter(Visit.id == visit_id)
            .with_for_update()
            .first()
        )
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visit not found",
            )
        if visit.clinic_id != current_user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )
        return visit

    def _ensure_expected_version(self, *, visit: Visit, expected_version: int) -> None:
        if visit.version != expected_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "VERSION_CONFLICT", "current_version": visit.version},
            )

    def _ensure_triage_authority(
        self,
        *,
        user,
        service_line: VisitServiceLine,
        is_doctor_fallback: bool,
    ) -> None:
        allowed_roles = SERVICE_LINE_TRIAGE_ROLES.get(service_line, set())
        user_role = self._role_value(user.role)
        allowed_role_values = {role.value for role in allowed_roles}
        if user_role in allowed_role_values:
            if is_doctor_fallback:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="is_doctor_fallback must be false for primary triage roles",
                )
            return

        if user_role == UserRole.DOCTOR.value:
            if not is_doctor_fallback:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Doctor triage requires is_doctor_fallback=true",
                )
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TRIAGE_ROLE_SERVICE_LINE_FORBIDDEN",
                "service_line": service_line.value,
            },
        )

    def _validate_payload(self, *, payload: TriageFinalizeRequest | TriageSupersedeRequest) -> None:
        missing_core_vitals = any(
            value is None
            for value in (
                payload.temp_c,
                payload.pulse_bpm,
                payload.rr_bpm,
                payload.sbp_mmhg,
                payload.dbp_mmhg,
            )
        )
        if missing_core_vitals and payload.missing_vitals_reason_code is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="missing_vitals_reason_code is required when core vitals are incomplete",
            )

        if self._requires_spo2(payload.danger_sign_codes) and payload.spo2_pct is None:
            if payload.missing_vitals_reason_code is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="spo2_pct is required for respiratory danger signs",
                )

        if payload.acuity_level == ClinicalPriorityLevel.CRITICAL:
            if not payload.triage_note or len(payload.triage_note.strip()) < 5:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="triage_note is required for CRITICAL acuity",
                )

        if payload.is_doctor_fallback:
            if payload.fallback_reason_code is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="fallback_reason_code is required for doctor fallback triage",
                )
            if payload.fallback_reason_code == TriageFallbackReasonCode.OTHER:
                text = (payload.fallback_reason_text or "").strip()
                if len(text) < 15:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="fallback_reason_text must be at least 15 characters for OTHER",
                    )
        else:
            if payload.fallback_reason_code is not None or (payload.fallback_reason_text or "").strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="fallback reason fields are allowed only for doctor fallback triage",
                )

        if payload.action == TriageFinalizeAction.REFER_OUT_IMMEDIATE:
            facility = (payload.referred_facility or "").strip()
            reason = (payload.referral_reason or "").strip()
            if len(facility) < 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="referred_facility is required for REFER_OUT_IMMEDIATE",
                )
            if len(reason) < 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="referral_reason is required for REFER_OUT_IMMEDIATE",
                )

    def _resolve_target_status(self, *, action: TriageFinalizeAction) -> VisitStatus:
        if action == TriageFinalizeAction.QUEUE_FOR_CONSULTATION:
            return VisitStatus.REGISTERED
        return VisitStatus.COMPLETED

    def _latest_priority_level(self, *, visit_id: UUID, clinic_id: UUID) -> ClinicalPriorityLevel:
        latest = (
            self.db.query(ClinicalPriorityEvent)
            .filter(
                ClinicalPriorityEvent.visit_id == visit_id,
                ClinicalPriorityEvent.clinic_id == clinic_id,
            )
            .order_by(ClinicalPriorityEvent.set_at.desc(), ClinicalPriorityEvent.id.desc())
            .first()
        )
        return latest.level if latest else ClinicalPriorityLevel.ROUTINE

    def _emit_triage_drafted_event(
        self,
        *,
        triage: TriageAssessment,
        current_user,
        visit: Visit,
        idempotency_key: str | None,
    ) -> None:
        self.event_service.emit(
            event_type="TRIAGE_ASSESSMENT_DRAFTED",
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="triage",
            payload={
                "triage_assessment_id": str(triage.id),
                "visit_id": str(visit.id),
                "patient_id": str(visit.patient_id),
                "clinic_id": str(visit.clinic_id),
                "record_status": triage.record_status.value,
                "assessed_by": str(triage.assessed_by),
                "assessed_by_role": triage.assessed_by_role,
                "assessed_at": triage.assessed_at.isoformat(),
                "idempotency_key": idempotency_key,
            },
        )

    def _emit_triage_signed_event(
        self,
        *,
        triage: TriageAssessment,
        current_user,
        visit: Visit,
        idempotency_key: str | None,
    ) -> None:
        self.event_service.emit(
            event_type="TRIAGE_ASSESSMENT_SIGNED",
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="triage",
            payload={
                "triage_assessment_id": str(triage.id),
                "visit_id": str(visit.id),
                "patient_id": str(visit.patient_id),
                "clinic_id": str(visit.clinic_id),
                "acuity_level": triage.acuity_level.value,
                "acuity_scale_version": triage.triage_scale_version.value,
                "assessed_by": str(triage.assessed_by),
                "assessed_by_role": triage.assessed_by_role,
                "assessed_at": triage.assessed_at.isoformat(),
                "is_doctor_fallback": triage.is_doctor_fallback,
                "fallback_reason_code": (
                    triage.fallback_reason_code.value if triage.fallback_reason_code else None
                ),
                "idempotency_key": idempotency_key,
            },
        )

    def _emit_triage_finalized_event(
        self,
        *,
        triage: TriageAssessment,
        current_user,
        visit: Visit,
        idempotency_key: str | None,
    ) -> None:
        self.event_service.emit(
            event_type="TRIAGE_ASSESSMENT_FINALIZED",
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="triage",
            payload={
                "triage_assessment_id": str(triage.id),
                "visit_id": str(visit.id),
                "patient_id": str(visit.patient_id),
                "clinic_id": str(visit.clinic_id),
                "acuity_level": triage.acuity_level.value,
                "acuity_scale_version": triage.triage_scale_version.value,
                "assessed_by": str(triage.assessed_by),
                "assessed_by_role": triage.assessed_by_role,
                "assessed_at": triage.assessed_at.isoformat(),
                "is_doctor_fallback": triage.is_doctor_fallback,
                "fallback_reason_code": (
                    triage.fallback_reason_code.value if triage.fallback_reason_code else None
                ),
                "idempotency_key": idempotency_key,
            },
        )

    def _emit_triage_superseded_event(
        self,
        *,
        previous: TriageAssessment,
        replacement: TriageAssessment,
        current_user,
        visit: Visit,
        idempotency_key: str | None,
    ) -> None:
        self.event_service.emit(
            event_type="TRIAGE_ASSESSMENT_SUPERSEDED",
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="triage",
            payload={
                "visit_id": str(visit.id),
                "patient_id": str(visit.patient_id),
                "clinic_id": str(visit.clinic_id),
                "previous_triage_assessment_id": str(previous.id),
                "replacement_triage_assessment_id": str(replacement.id),
                "acuity_level": replacement.acuity_level.value,
                "acuity_scale_version": replacement.triage_scale_version.value,
                "assessed_by": str(replacement.assessed_by),
                "assessed_by_role": replacement.assessed_by_role,
                "assessed_at": replacement.assessed_at.isoformat(),
                "idempotency_key": idempotency_key,
            },
        )

    def _emit_priority_event_if_changed(
        self,
        *,
        previous: ClinicalPriorityLevel,
        current: ClinicalPriorityLevel,
        current_user,
        visit: Visit,
        assessed_at: datetime,
    ) -> None:
        if previous == current:
            return
        event_type = "PRIORITY_ESCALATED" if self._priority_rank(current) > self._priority_rank(previous) else "PRIORITY_DEESCALATED"
        self.event_service.emit(
            event_type=event_type,
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="clinical_priority_service",
            payload={
                "visit_id": str(visit.id),
                "patient_id": str(visit.patient_id),
                "clinic_id": str(visit.clinic_id),
                "from_level": previous.value,
                "to_level": current.value,
                "source": ClinicalPrioritySource.TRIAGE.value,
                "reason": "triage_assessment",
                "set_by": str(current_user.id),
                "set_at": assessed_at.isoformat(),
            },
        )

    def _emit_visit_status_event(
        self,
        *,
        visit: Visit,
        current_user,
        from_status: VisitStatus,
        to_status: VisitStatus,
        triage_assessment_id: UUID,
        idempotency_key: str | None,
    ) -> None:
        self.event_service.emit(
            event_type="ENTRY_AMENDED",
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="clinical",
            payload={
                "entity": "visit",
                "action": "status_transition",
                "visit_id": str(visit.id),
                "from_status": from_status.value,
                "to_status": to_status.value,
                "source": "manual",
                "triage_assessment_id": str(triage_assessment_id),
                "idempotency_key": idempotency_key,
            },
        )

    def _priority_rank(self, level: ClinicalPriorityLevel) -> int:
        rank = {
            ClinicalPriorityLevel.ROUTINE: 0,
            ClinicalPriorityLevel.URGENT: 1,
            ClinicalPriorityLevel.CRITICAL: 2,
        }
        return rank[level]

    def _requires_spo2(self, danger_sign_codes: list[str]) -> bool:
        if not danger_sign_codes:
            return False
        normalized = " ".join(danger_sign_codes).upper()
        return any(token in normalized for token in RESPIRATORY_SIGNAL_TOKENS)

    def _role_value(self, role) -> str:
        if isinstance(role, UserRole):
            return role.value
        value = getattr(role, "value", None)
        if isinstance(value, str):
            return value
        return str(role)
