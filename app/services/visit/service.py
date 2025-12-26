# app/services/visit/service.py

# app/services/visit/service.py

from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.services.visit.guards import guard_can_transition
from app.shared.enums import VisitStatus
from app.core.logging import domain_log


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

    # ============================================================
    # CANONICAL TRANSITION METHOD (ONLY WRITE PATH)
    # ============================================================

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
        - Guard-enforced lifecycle
        - Atomic state + audit persistence
        - Post-commit domain logging
        """

        # 🔒 Phase 3.2 — Row-level lock
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
                visit.completed_at = datetime.utcnow()

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

        # 4️⃣ Post-commit observability (forensic truth)
        domain_log(
            event="visit.status.transition",
            payload={
                "visit_id": str(visit.id),
                "from_status": from_status,
                "to_status": to_status,
                "actor_id": str(user.id),
                "actor_role": user.role,
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

        # Delegate to canonical transition (lock + audit)
        return self.transition_visit(
            visit_id=visit_id,
            to_status=VisitStatus.PHARMACY_PENDING,
            user=user,
            request_id=request_id,
        )

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




# Before adding row-level locking

# # app/services/visit/service.py

# from datetime import datetime
# from uuid import UUID

# from fastapi import HTTPException, status
# from sqlalchemy.exc import SQLAlchemyError

# from app.models.visit import Visit
# from app.models.visit_status_history import VisitStatusHistory
# from app.services.visit.guards import guard_can_transition
# from app.shared.enums import VisitStatus


# class VisitService:
#     def __init__(self, db):
#         self.db = db

#     def transition_visit(
#         self,
#         visit_id: UUID,
#         to_status: VisitStatus,
#         user,
#     ) -> Visit:
#         visit = self._get_visit_or_fail(visit_id)

#         # 🔒 Central safety gate (unchanged)
#         guard_can_transition(
#             db=self.db,
#             visit=visit,
#             to_status=to_status,
#             user=user,
#         )

#         from_status = visit.status

#         try:
#             # 1️⃣ Update current Visit truth
#             visit.status = to_status

#             if to_status == VisitStatus.COMPLETED:
#                 visit.completed_at = datetime.utcnow()

#             self.db.add(visit)

#             # 2️⃣ Append immutable status history
#             history = VisitStatusHistory(
#                 visit_id=visit.id,
#                 from_status=from_status,
#                 to_status=to_status,
#                 changed_by=user.id,
#             )
#             self.db.add(history)

#             # 3️⃣ Atomic commit
#             self.db.commit()

#         except SQLAlchemyError:
#             self.db.rollback()
#             raise

#         self.db.refresh(visit)
#         return visit

#     # Get all allowed transitions for a visit and user
#     def get_allowed_transitions(self, visit: Visit, user) -> list[VisitStatus]:
#         allowed = []

#         for status in VisitStatus:
#             try:
#                 guard_can_transition(
#                     db=self.db,
#                     visit=visit,
#                     to_status=status,
#                     user=user,
#                 )
#                 allowed.append(status)
#             except Exception:
#                 continue

#         return allowed

#     def get_visit_timeline(self, visit_id: UUID):
#         return (
#             self.db.query(VisitStatusHistory)
#             .filter(VisitStatusHistory.visit_id == visit_id)
#             .order_by(VisitStatusHistory.created_at.asc())
#             .all()
#         )

    # def _get_visit_or_fail(self, visit_id: UUID) -> Visit:
    #     visit = (
    #         self.db.query(Visit)
    #         .filter(Visit.id == visit_id)
    #         .first()
    #     )

    #     if not visit:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Visit not found",
    #         )

    #     return visit
