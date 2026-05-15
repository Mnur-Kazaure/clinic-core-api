# app/services/visit/service.py
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.models.doctor_service_line import DoctorServiceLine
from app.models.triage_assessment import TriageAssessment
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.services.visit.guards import guard_can_transition
from app.core.guards.patient_guards import ensure_patient_in_clinic
from app.core.guards.user_guards import ensure_owner_for_service_line
from app.services.service_line_service import ServiceLineService
from app.shared.enums import (
    VisitStatus,
    AdmissionStatus,
    ClinicalPriorityLevel,
    UserRole,
    VisitServiceLine,
)
from app.services.event_service import EventService
from app.schemas.visit import VisitCreateRequest

from app.services.visit.outstanding import compute_outstanding
from app.shared.enums import VisitOverrideReasonCode

class VisitService:
    """
    VisitService is the SINGLE AUTHORITY for Visit state transitions.

    Invariants:
    - Visit status is mutated in exactly one place
    - All transitions are guarded
    - All mutations are atomic
    - All transitions are audited
    - All writes are row-locked
    """

    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    # ============================================================
    # CANONICAL TRANSITION METHOD (ONLY WRITE PATH)
    # ============================================================

    def start_visit(self, payload: VisitCreateRequest, current_user) -> Visit:
        """
        Create a visit with strict clinic and role invariants.
        """
        try:
            ensure_patient_in_clinic(
                self.db,
                payload.patient_id,
                current_user.clinic_id,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            )

        (
            resolved_service_line,
            resolved_service_line_id,
            requires_doctor,
            service_line_department_id,
        ) = self._resolve_visit_service_line(payload=payload, current_user=current_user)

        self._validate_department_scope(
            current_user=current_user,
            service_line_department_id=service_line_department_id,
        )

        if requires_doctor and payload.assigned_doctor_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="assigned_doctor_id is required for selected service line",
            )

        if payload.assigned_doctor_id is not None:
            self._validate_owner_for_service_line(
                clinic_id=current_user.clinic_id,
                assigned_owner_id=payload.assigned_doctor_id,
                service_line=resolved_service_line,
                service_line_id=resolved_service_line_id,
            )

        # 🔒 Prevent multiple active visits for same patient
        existing = (
            self.db.query(Visit)
            .filter(
                Visit.patient_id == payload.patient_id,
                Visit.clinic_id == current_user.clinic_id,
                Visit.status.notin_(
                    [VisitStatus.COMPLETED, VisitStatus.CANCELLED]
                ),
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active visit already exists for this patient",
            )

        visit = Visit(
            clinic_id=current_user.clinic_id,
            patient_id=payload.patient_id,
            assigned_doctor_id=payload.assigned_doctor_id,
            status=VisitStatus.REGISTERED,
            service_line=resolved_service_line,
            service_line_id=resolved_service_line_id,
            linked_follow_up_id=payload.linked_follow_up_id,
            started_at=datetime.now(timezone.utc),  # 🔒 Legal start of care
        )

        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)

        self.event_service.emit(
            event_type="VISIT_REGISTERED",
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            emitter="visit",
            payload={
                "visit_id": str(visit.id),
                "assigned_doctor_id": (
                    str(visit.assigned_doctor_id) if visit.assigned_doctor_id else None
                ),
                "service_line_id": (
                    str(visit.service_line_id) if visit.service_line_id else None
                ),
            },
        )

        # Auto-link visit to active admission (if any)
        from app.models.admission import Admission
        from app.models.admission_visit_link import AdmissionVisitLink

        active_admission = (
            self.db.query(Admission)
            .filter(
                Admission.patient_id == payload.patient_id,
                Admission.clinic_id == current_user.clinic_id,
                Admission.status == AdmissionStatus.ACTIVE,
            )
            .first()
        )
        if active_admission:
            link = AdmissionVisitLink(
                clinic_id=current_user.clinic_id,
                admission_id=active_admission.id,
                visit_id=visit.id,
                linked_at=datetime.now(timezone.utc),
            )
            self.db.add(link)
            self.db.commit()

        return visit

    def _resolve_visit_service_line(
        self,
        *,
        payload: VisitCreateRequest,
        current_user,
    ) -> tuple[VisitServiceLine, UUID | None, bool, UUID | None]:
        if payload.service_line_id is None:
            default_service_line_id = self._resolve_default_service_line_id_for_legacy(
                clinic_id=current_user.clinic_id,
                service_line=payload.service_line,
            )
            service_line_department_id: UUID | None = None
            if default_service_line_id is not None:
                service_line_department_id = ServiceLineService(self.db).resolve_department_id(
                    clinic_id=current_user.clinic_id,
                    service_line_id=default_service_line_id,
                )
            return (
                payload.service_line,
                default_service_line_id,
                True,
                service_line_department_id,
            )

        service_line_service = ServiceLineService(self.db)
        selected_line = service_line_service.get_or_404(
            clinic_id=current_user.clinic_id,
            service_line_id=payload.service_line_id,
        )
        if not selected_line.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected service line is inactive",
            )

        if not service_line_service.is_leaf(
            clinic_id=current_user.clinic_id,
            service_line_id=selected_line.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="service_line_id must reference a leaf service line",
            )

        requires_doctor = service_line_service.resolve_requires_doctor(
            clinic_id=current_user.clinic_id,
            service_line_id=selected_line.id,
        )
        root = service_line_service.resolve_root(
            clinic_id=current_user.clinic_id,
            service_line_id=selected_line.id,
        )
        legacy_line = self._legacy_service_line_from_line(
            selected_name=selected_line.name,
            root_name=root.name,
        )
        service_line_department_id = service_line_service.resolve_department_id(
            clinic_id=current_user.clinic_id,
            service_line_id=selected_line.id,
        )
        return legacy_line, selected_line.id, requires_doctor, service_line_department_id

    def _resolve_default_service_line_id_for_legacy(
        self,
        *,
        clinic_id: UUID,
        service_line: VisitServiceLine,
    ) -> UUID | None:
        service_line_service = ServiceLineService(self.db)
        tree = service_line_service.list_tree(
            clinic_id=clinic_id,
            include_inactive=False,
            department_id=None,
            include_global_roots=True,
        )

        target_names = {
            VisitServiceLine.OPD: {"gopd", "consultation"},
            VisitServiceLine.ANC: {"anc"},
            VisitServiceLine.MATERNITY: {"maternity"},
        }
        wanted = target_names.get(service_line, set())
        for root in tree:
            root_name = str(root["name"]).strip().lower()
            if root_name in wanted and not root["children"]:
                return root["id"]
            for child in root["children"]:
                child_name = str(child["name"]).strip().lower()
                if child_name in wanted:
                    return child["id"]
        return None

    def _legacy_service_line_from_line(
        self,
        *,
        selected_name: str,
        root_name: str,
    ) -> VisitServiceLine:
        selected_normalized = selected_name.strip().lower()
        root_normalized = root_name.strip().lower()

        if selected_normalized == "anc":
            return VisitServiceLine.ANC
        if selected_normalized == "maternity":
            return VisitServiceLine.MATERNITY
        if root_normalized == "maternal & child health":
            return VisitServiceLine.MATERNITY
        return VisitServiceLine.OPD

    def _validate_department_scope(
        self,
        *,
        current_user,
        service_line_department_id: UUID | None,
    ) -> None:
        if service_line_department_id is None:
            return

        selected_department_id = getattr(current_user, "current_department_id", None)
        if selected_department_id is None:
            return

        if service_line_department_id != selected_department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service line does not belong to the active department context",
            )

    def _validate_owner_for_service_line(
        self,
        *,
        clinic_id: UUID,
        assigned_owner_id: UUID,
        service_line: VisitServiceLine,
        service_line_id: UUID | None,
    ) -> None:
        if service_line_id is None:
            try:
                ensure_owner_for_service_line(
                    self.db,
                    assigned_owner_id,
                    clinic_id,
                    service_line,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(exc),
                )
            return

        mapping = (
            self.db.query(DoctorServiceLine)
            .join(User, User.id == DoctorServiceLine.doctor_id)
            .filter(
                DoctorServiceLine.doctor_id == assigned_owner_id,
                DoctorServiceLine.service_line_id == service_line_id,
                User.clinic_id == clinic_id,
                User.is_active == True,
            )
            .first()
        )
        if mapping is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned owner is not linked to selected service line",
            )

    def get_active_visit_for_patient(
        self,
        *,
        clinic_id,
        patient_id,
    ) -> Visit | None:
        return (
            self.db.query(Visit)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.patient_id == patient_id,
                Visit.status.notin_(
                    [VisitStatus.COMPLETED, VisitStatus.CANCELLED]
                ),
            )
            .order_by(Visit.created_at.desc())
            .first()
        )

    def reassign_owner(
        self,
        *,
        visit_id: UUID,
        new_owner_id: UUID,
        new_service_line: VisitServiceLine | None,
        user,
        expected_version: int,
        reason: str | None = None,
    ) -> Visit:
        """
        Reassign visit owner and optionally hand over the visit service line.

        Authorization:
        - Reception / Clinic Admin / Admin can reassign any non-terminal visit in clinic.
        - Assigned owner can hand over to a colleague in the same service-line role.
        - Assigned CHEW can hand over ANC -> MATERNITY to a midwife.
        """
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

        if visit.clinic_id != user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )

        if visit.status in {VisitStatus.COMPLETED, VisitStatus.CANCELLED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot reassign a completed or cancelled visit",
            )

        if visit.version != expected_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "VERSION_CONFLICT",
                    "current_version": visit.version,
                },
            )

        current_service_line = visit.service_line
        target_service_line = new_service_line or current_service_line

        service_line_owner_role = {
            VisitServiceLine.OPD: UserRole.DOCTOR,
            VisitServiceLine.ANC: UserRole.CHEW,
            VisitServiceLine.MATERNITY: UserRole.MIDWIFE,
        }
        current_owner_role = service_line_owner_role[current_service_line]

        admin_roles = {
            UserRole.RECEPTION,
            UserRole.CLINIC_ADMIN,
            UserRole.ADMIN,
        }
        is_admin = user.role in admin_roles
        is_assigned_owner = (
            user.role == current_owner_role
            and visit.assigned_doctor_id == user.id
        )
        if not is_admin and not is_assigned_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not permitted to reassign this visit",
            )

        if target_service_line != current_service_line:
            allow_assigned_chew_handover = (
                is_assigned_owner
                and user.role == UserRole.CHEW
                and current_service_line == VisitServiceLine.ANC
                and target_service_line == VisitServiceLine.MATERNITY
            )
            if not is_admin and not allow_assigned_chew_handover:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not permitted to change service line",
                )

        try:
            ensure_owner_for_service_line(
                self.db,
                new_owner_id,
                user.clinic_id,
                target_service_line,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

        from_owner_id = visit.assigned_doctor_id
        from_service_line = current_service_line
        if from_owner_id == new_owner_id and from_service_line == target_service_line:
            return visit

        visit.assigned_doctor_id = new_owner_id
        visit.service_line = target_service_line
        visit.version = (visit.version or 0) + 1
        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)

        self.event_service.emit(
            event_type="ENTRY_AMENDED",
            actor_id=user.id,
            actor_role=user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="clinical",
            payload={
                "entity": "visit",
                "action": "owner_reassigned",
                "visit_id": str(visit.id),
                "from_service_line": from_service_line.value,
                "to_service_line": visit.service_line.value,
                "from_owner_id": str(from_owner_id) if from_owner_id else None,
                "to_owner_id": str(new_owner_id),
                "reason": (reason or "").strip() or "workflow_handover",
            },
        )
        return visit


    def transition_visit(
        self,
        visit_id: UUID,
        to_status: VisitStatus,
        user,
        request_id: Optional[str] = None,
        *,
        expected_version: int | None = None,
        mode: str = "normal",
        override_reason_code: VisitOverrideReasonCode | None = None,
        override_reason_text: str | None = None,
        idempotency_key: str | None = None,
    ) -> Visit:
        """
        Transition a Visit to a new state.

        Guarantees:
        - Row-level locking (SELECT ... FOR UPDATE)
        - Clinic boundary enforced BEFORE mutation (fail-fast)
        - Guard-enforced lifecycle
        - Atomic state + audit persistence
        - Post-commit domain logging
        """

        # 🔒 Row-level lock
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

        # ✅ Clinic boundary (FAIL FAST — BEFORE guards/mutation)
        # System actor bypass for internal automation
        if user.role != UserRole.SYSTEM and visit.clinic_id != user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )

        # ✅ Optimistic concurrency (API callers must supply expected_version).
        if user.role != UserRole.SYSTEM:
            if expected_version is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="expected_version is required",
                )
            if visit.version != expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "VERSION_CONFLICT",
                        "current_version": visit.version,
                    },
                )

        # TRIAGED state is contract-driven through /triage/finalize.
        if to_status == VisitStatus.TRIAGED and user.role != UserRole.SYSTEM:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TRIAGE_USE_FINALIZE_ENDPOINT"},
            )

        if visit.status == VisitStatus.TRIAGED and to_status == VisitStatus.IN_CONSULTATION:
            active_triage = (
                self.db.query(TriageAssessment)
                .filter(
                    TriageAssessment.visit_id == visit.id,
                    TriageAssessment.superseded_at.is_(None),
                )
                .first()
            )
            if active_triage is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "RETRIAGE_REQUIRED"},
                )

        # 🔐 Guards operate on locked row
        guard_can_transition(
            db=self.db,
            visit=visit,
            to_status=to_status,
            user=user,
        )

        from_status = visit.status

        outstanding_snapshot: dict | None = None
        completion_mode: str | None = None

        # ------------------------------------------------------------
        # Completion is outstanding-aware and supports override mode.
        # ------------------------------------------------------------
        if to_status == VisitStatus.COMPLETED:
            outstanding_snapshot = compute_outstanding(self.db, visit_id=visit.id)
            has_outstanding = bool(outstanding_snapshot.get("has_outstanding"))

            if mode not in {"normal", "override"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid completion mode",
                )

            allowed_override = user.role in {
                UserRole.RECEPTION,
                UserRole.CLINIC_ADMIN,
                UserRole.ADMIN,
            }

            if mode == "normal":
                if has_outstanding:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "code": "VISIT_HAS_OUTSTANDING_WORK",
                            "allowed_override": allowed_override,
                            "outstanding": {
                                "pending_labs_count": outstanding_snapshot.get(
                                    "pending_labs_count", 0
                                ),
                                "unfulfilled_prescriptions_count": outstanding_snapshot.get(
                                    "unfulfilled_prescriptions_count", 0
                                ),
                            },
                            "override_reason_codes": [
                                code.value for code in VisitOverrideReasonCode
                            ],
                        },
                    )
                completion_mode = "normal"
            else:
                # override completion
                if not allowed_override:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Override completion not permitted for role",
                    )
                if override_reason_code is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="override_reason_code is required for override completion",
                    )
                if override_reason_code == VisitOverrideReasonCode.OTHER:
                    text = (override_reason_text or "").strip()
                    if len(text) < 10:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="override_reason_text must be at least 10 characters for OTHER",
                        )
                completion_mode = "override"

        try:
            # 1️⃣ Update Visit truth
            visit.status = to_status

            if to_status == VisitStatus.COMPLETED:
                visit.completed_at = datetime.now(timezone.utc)
            else:
                # Keep completed_at aligned with current status.
                visit.completed_at = None

            # bump optimistic token
            visit.version = (visit.version or 0) + 1
            self.db.add(visit)

            # 2️⃣ Append immutable history
            history = VisitStatusHistory(
                visit_id=visit.id,
                from_status=from_status,
                to_status=to_status,
                changed_by=user.id,
                source=(
                    "auto"
                    if user.role == UserRole.SYSTEM
                    else ("override" if completion_mode == "override" else "manual")
                ),
                reason_code=(
                    override_reason_code.value
                    if completion_mode == "override" and override_reason_code
                    else None
                ),
                reason_text=(
                    (override_reason_text or "").strip()
                    if completion_mode == "override"
                    and override_reason_code == VisitOverrideReasonCode.OTHER
                    else None
                ),
                pending_labs_count_snapshot=(
                    outstanding_snapshot.get("pending_labs_count")
                    if completion_mode == "override" and outstanding_snapshot
                    else None
                ),
                unfulfilled_prescriptions_count_snapshot=(
                    outstanding_snapshot.get("unfulfilled_prescriptions_count")
                    if completion_mode == "override" and outstanding_snapshot
                    else None
                ),
                idempotency_key=idempotency_key,
            )
            self.db.add(history)

            # 3️⃣ Atomic commit
            self.db.commit()

        except SQLAlchemyError:
            self.db.rollback()
            raise

        # 4️⃣ Post-commit observability
        self.event_service.emit(
            event_type="ENTRY_AMENDED",
            actor_id=user.id,
            actor_role=user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="clinical",
            payload={
                "entity": "visit",
                "action": "status_transition",
                "visit_id": str(visit.id),
                "from_status": from_status,
                "to_status": to_status,
                "source": "manual",
                "request_id": request_id,
                "completion_mode": completion_mode,
                "outstanding_snapshot": (
                    {
                        "pending_labs_count": outstanding_snapshot.get(
                            "pending_labs_count"
                        ),
                        "unfulfilled_prescriptions_count": outstanding_snapshot.get(
                            "unfulfilled_prescriptions_count"
                        ),
                    }
                    if outstanding_snapshot
                    else None
                ),
                "idempotency_key": idempotency_key,
            },
        )

        self.db.refresh(visit)
        return visit



    # ============================================================
    # AUTO-ADVANCE (SAFE, IDEMPOTENT)
    # ============================================================

    def auto_advance_after_lab(
        self,
        visit_id: UUID,
        user,
        request_id: Optional[str] = None,
    ) -> Visit:
        """
        Auto-advance Visit after lab completion.

        Rules:
        - Read without lock
        - Delegate locking + mutation to canonical transition
        - Idempotent and safe to retry
        """

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

        # Already moved → no-op (idempotent)
        if visit.status != VisitStatus.LAB_COMPLETED:
            return visit

    # ============================================================
    # QUEUE DERIVATION (PRIORITY-AWARE)
    # ============================================================

    def get_queue_for_clinic(
        self,
        clinic_id,
        status: VisitStatus | None = None,
        department_id: UUID | None = None,
    ) -> list[Visit]:
        q = self.db.query(Visit).filter(Visit.clinic_id == clinic_id)
        if status is not None:
            q = q.filter(Visit.status == status)
        else:
            q = q.filter(
                Visit.status.notin_(
                    [VisitStatus.COMPLETED, VisitStatus.CANCELLED]
                )
            )
        visits = q.all()
        if department_id is not None:
            visits = self._filter_visits_by_department(
                visits=visits,
                clinic_id=clinic_id,
                department_id=department_id,
            )
        return self._order_visits_by_priority(visits, clinic_id)

    def get_queue_for_doctor(
        self,
        clinic_id,
        doctor_id,
        status: VisitStatus | None = None,
        department_id: UUID | None = None,
    ) -> list[Visit]:
        q = (
            self.db.query(Visit)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.assigned_doctor_id == doctor_id,
            )
        )
        if status is not None:
            q = q.filter(Visit.status == status)
        else:
            q = q.filter(
                Visit.status.notin_(
                    [VisitStatus.COMPLETED, VisitStatus.CANCELLED]
                )
            )
        visits = q.all()
        if department_id is not None:
            visits = self._filter_visits_by_department(
                visits=visits,
                clinic_id=clinic_id,
                department_id=department_id,
            )
        return self._order_visits_by_priority(visits, clinic_id)

    def get_queue_for_owner_by_service_line(
        self,
        clinic_id,
        owner_id,
        service_line,
        status: VisitStatus | None = None,
        department_id: UUID | None = None,
    ) -> list[Visit]:
        q = (
            self.db.query(Visit)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.assigned_doctor_id == owner_id,
                Visit.service_line == service_line,
            )
        )
        if status is not None:
            q = q.filter(Visit.status == status)
        else:
            q = q.filter(
                Visit.status.notin_(
                    [VisitStatus.COMPLETED, VisitStatus.CANCELLED]
                )
            )
        visits = q.all()
        if department_id is not None:
            visits = self._filter_visits_by_department(
                visits=visits,
                clinic_id=clinic_id,
                department_id=department_id,
            )
        return self._order_visits_by_priority(visits, clinic_id)

    def _filter_visits_by_department(
        self,
        *,
        visits: list[Visit],
        clinic_id: UUID,
        department_id: UUID,
    ) -> list[Visit]:
        if not visits:
            return []

        service_line_service = ServiceLineService(self.db)
        department_cache: dict[UUID, UUID | None] = {}
        filtered: list[Visit] = []

        for visit in visits:
            if visit.service_line_id is None:
                continue

            resolved = department_cache.get(visit.service_line_id)
            if visit.service_line_id not in department_cache:
                resolved = service_line_service.resolve_department_id(
                    clinic_id=clinic_id,
                    service_line_id=visit.service_line_id,
                )
                department_cache[visit.service_line_id] = resolved

            if resolved == department_id:
                filtered.append(visit)

        return filtered

    def _order_visits_by_priority(
        self,
        visits: list[Visit],
        clinic_id,
    ) -> list[Visit]:
        if not visits:
            return []

        visit_ids = [visit.id for visit in visits]

        triage_rows = (
            self.db.query(
                VisitStatusHistory.visit_id,
                func.min(VisitStatusHistory.created_at).label("triaged_at"),
            )
            .filter(
                VisitStatusHistory.visit_id.in_(visit_ids),
                VisitStatusHistory.to_status == VisitStatus.TRIAGED,
            )
            .group_by(VisitStatusHistory.visit_id)
            .all()
        )
        triaged_at_map = {
            row.visit_id: row.triaged_at for row in triage_rows
        }

        priority_events = (
            self.db.query(ClinicalPriorityEvent)
            .filter(
                ClinicalPriorityEvent.visit_id.in_(visit_ids),
                ClinicalPriorityEvent.clinic_id == clinic_id,
            )
            .order_by(
                ClinicalPriorityEvent.visit_id.asc(),
                ClinicalPriorityEvent.set_at.desc(),
                ClinicalPriorityEvent.id.desc(),
            )
            .all()
        )
        latest_priority = {}
        for event in priority_events:
            if event.visit_id not in latest_priority:
                latest_priority[event.visit_id] = event.level

        priority_rank = {
            ClinicalPriorityLevel.CRITICAL: 0,
            ClinicalPriorityLevel.URGENT: 1,
            ClinicalPriorityLevel.ROUTINE: 2,
        }

        def _ensure_aware(value: datetime | None) -> datetime:
            if value is None:
                return datetime.now(timezone.utc)
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        def sort_key(visit: Visit):
            level = latest_priority.get(
                visit.id, ClinicalPriorityLevel.ROUTINE
            )
            triaged_at = _ensure_aware(triaged_at_map.get(visit.id) or visit.started_at)
            started_at = _ensure_aware(visit.started_at)
            return (
                priority_rank[level],
                triaged_at,
                started_at,
                str(visit.id),
            )

        return sorted(visits, key=sort_key)

    # ============================================================
    # READ-ONLY HELPERS (NO LOCKING, NO LOGGING)
    # ============================================================

    def get_allowed_transitions(self, visit: Visit, user) -> list[VisitStatus]:
        """
        Returns all valid transitions for a visit & user.
        Read-only.
        """
        allowed = []

        for status in VisitStatus:
            try:
                guard_can_transition(
                    db=self.db,
                    visit=visit,
                    to_status=status,
                    user=user,
                )
                allowed.append(status)
            except Exception:
                continue

        return allowed

    def get_visit_timeline(self, visit_id: UUID):
        """
        Returns immutable visit timeline.
        Read-only.
        """
        return (
            self.db.query(VisitStatusHistory)
            .filter(VisitStatusHistory.visit_id == visit_id)
            .order_by(VisitStatusHistory.created_at.asc())
            .all()
        )
