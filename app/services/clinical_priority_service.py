# app/services/clinical_priority_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.models.visit import Visit
from app.services.event_service import EventService
from app.shared.enums import ClinicalPriorityLevel, ClinicalPrioritySource, UserRole


PRIORITY_SEVERITY = {
    ClinicalPriorityLevel.CRITICAL: 3,
    ClinicalPriorityLevel.URGENT: 2,
    ClinicalPriorityLevel.ROUTINE: 1,
}


class ClinicalPriorityService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    def _latest_priority_event(self, visit_id: UUID, clinic_id: UUID) -> ClinicalPriorityEvent | None:
        return (
            self.db.query(ClinicalPriorityEvent)
            .filter(
                ClinicalPriorityEvent.visit_id == visit_id,
                ClinicalPriorityEvent.clinic_id == clinic_id,
            )
            .order_by(
                ClinicalPriorityEvent.set_at.desc(),
                ClinicalPriorityEvent.id.desc(),
            )
            .first()
        )

    def set_priority(
        self,
        *,
        visit_id: UUID,
        level: ClinicalPriorityLevel,
        source: ClinicalPrioritySource,
        reason: str,
        current_user,
    ) -> ClinicalPriorityEvent:
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

        if current_user.role not in {
            UserRole.RECEPTION,
            UserRole.DOCTOR,
            UserRole.CLINIC_ADMIN,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Priority access denied",
            )

        latest = self._latest_priority_event(visit_id, current_user.clinic_id)
        current_level = (
            latest.level if latest else ClinicalPriorityLevel.ROUTINE
        )

        if level == current_level:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Priority already set to requested level",
            )

        now = datetime.now(timezone.utc)
        priority_event = ClinicalPriorityEvent(
            clinic_id=current_user.clinic_id,
            visit_id=visit.id,
            patient_id=visit.patient_id,
            level=level,
            source=source,
            reason=reason,
            set_by=current_user.id,
            set_at=now,
        )
        self.db.add(priority_event)
        self.db.commit()
        self.db.refresh(priority_event)

        if PRIORITY_SEVERITY[level] > PRIORITY_SEVERITY[current_level]:
            event_type = "PRIORITY_ESCALATED"
        else:
            event_type = "PRIORITY_DEESCALATED"

        payload = {
            "visit_id": str(visit.id),
            "patient_id": str(visit.patient_id),
            "clinic_id": str(visit.clinic_id),
            "from_level": current_level.value,
            "to_level": level.value,
            "source": source.value,
            "reason": reason,
            "set_by": str(current_user.id),
            "set_at": now.isoformat(),
        }
        self.event_service.emit(
            event_type=event_type,
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="clinical_priority_service",
            payload=payload,
        )

        return priority_event
