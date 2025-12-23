# app/services/visit/service.py

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.services.visit.guards import guard_can_transition
from app.shared.enums import VisitStatus


class VisitService:
    def __init__(self, db):
        self.db = db

    def transition_visit(
        self,
        visit_id: UUID,
        to_status: VisitStatus,
        user,
    ) -> Visit:
        visit = self._get_visit_or_fail(visit_id)

        # 🔒 Central safety gate (unchanged)
        guard_can_transition(
            db=self.db,
            visit=visit,
            to_status=to_status,
            user=user,
        )

        from_status = visit.status

        try:
            # 1️⃣ Update current Visit truth
            visit.status = to_status

            if to_status == VisitStatus.COMPLETED:
                visit.completed_at = datetime.utcnow()

            self.db.add(visit)

            # 2️⃣ Append immutable status history
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

        self.db.refresh(visit)
        return visit

    # Get all allowed transitions for a visit and user
    def get_allowed_transitions(self, visit: Visit, user) -> list[VisitStatus]:
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
        return (
            self.db.query(VisitStatusHistory)
            .filter(VisitStatusHistory.visit_id == visit_id)
            .order_by(VisitStatusHistory.created_at.asc())
            .all()
        )

    def _get_visit_or_fail(self, visit_id: UUID) -> Visit:
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

        return visit






# # app/modules/visit/service.py
# # app/services/visit/service.py
# from datetime import datetime
# from uuid import UUID

# from app.models.visit import Visit
# from app.services.visit.guards import guard_can_transition
# from app.shared.enums import VisitStatus
# # from app.services.audit_service import audit_log
# from app.models.visit_status_history import VisitStatusHistory
# from fastapi import HTTPException, status
# from app.models.visit import Visit


# class VisitService:
#     def __init__(self, db):
#         self.db = db

#     def transition_visit(self, visit_id: UUID, to_status: VisitStatus, user):
#         visit = self._get_visit_or_fail(visit_id)

#         guard_can_transition(
#             db=self.db,
#             visit=visit,
#             to_status=to_status,
#             user=user,
#         )

#         from_status = visit.status
#         visit.status = to_status

#         if to_status == VisitStatus.COMPLETED:
#             visit.completed_at = datetime.utcnow()

#         self.db.commit()
#         self.db.refresh(visit)

#         # audit_log(
#         #     db=self.db,
#         #     clinic_id=visit.clinic_id,
#         #     user_id=user.id,
#         #     action="VISIT_STATUS_CHANGED",
#         #     entity="visits",
#         #     entity_id=visit.id,
#         #     metadata={
#         #         "from": from_status,
#         #         "to": to_status,
#         #     },
#         # )

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





#     def get_visit_timeline(self, visit_id):
#         return (
#             self.db.query(VisitStatusHistory)
#             .filter(VisitStatusHistory.visit_id == visit_id)
#             .order_by(VisitStatusHistory.created_at.asc())
#             .all()
#         )
    

#     # Just added this as you gave me
#     def _get_visit_or_fail(self, visit_id):
#         visit = (
#             self.db
#             .query(Visit)
#             .filter(Visit.id == visit_id)
#             .first()
#         )

#         if not visit:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Visit not found",
#             )

#         return visit


