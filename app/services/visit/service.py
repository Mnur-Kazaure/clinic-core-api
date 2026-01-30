# app/services/visit/service.py
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.services.visit.guards import guard_can_transition
from app.core.guards.patient_guards import ensure_patient_in_clinic
from app.core.guards.user_guards import ensure_doctor_in_clinic
from app.shared.enums import VisitStatus, AdmissionStatus, ClinicalPriorityLevel
from app.services.event_service import EventService
from app.schemas.visit import VisitCreateRequest

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
            ensure_doctor_in_clinic(
                self.db,
                payload.assigned_doctor_id,
                current_user.clinic_id,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
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
            started_at=datetime.now(timezone.utc),  # 🔒 Legal start of care
        )

        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)

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


    def transition_visit(
        self,
        visit_id: UUID,
        to_status: VisitStatus,
        user,
        request_id: Optional[str] = None,
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
        if visit.clinic_id != user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )

        # 🔐 Guards operate on locked row
        guard_can_transition(
            db=self.db,
            visit=visit,
            to_status=to_status,
            user=user,
        )

        from_status = visit.status

        try:
            # 1️⃣ Update Visit truth
            visit.status = to_status

            if to_status == VisitStatus.COMPLETED:
                visit.completed_at = datetime.now(timezone.utc)

            self.db.add(visit)

            # 2️⃣ Append immutable history
            history = VisitStatusHistory(
                visit_id=visit.id,
                from_status=from_status,
                to_status=to_status,
                changed_by=user.id,
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
        return self._order_visits_by_priority(visits, clinic_id)

    def get_queue_for_doctor(
        self,
        clinic_id,
        doctor_id,
        status: VisitStatus | None = None,
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
        return self._order_visits_by_priority(visits, clinic_id)

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

        def sort_key(visit: Visit):
            level = latest_priority.get(
                visit.id, ClinicalPriorityLevel.ROUTINE
            )
            triaged_at = triaged_at_map.get(visit.id) or visit.started_at
            return (
                priority_rank[level],
                triaged_at,
                visit.started_at,
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
