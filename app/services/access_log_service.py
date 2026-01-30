# app/services/access_log_service.py
from app.models.access_log import AccessLog
from app.services.event_service import EventService


class AccessLogService:
    def __init__(self, db):
        self.db = db
        self.event_service = EventService(db)

    def log_search(
        self,
        *,
        actor,
        clinic_id,
        purpose_of_use: str,
        reason: str,
        session_id: str | None = None,
        device_id: str | None = None,
    ) -> AccessLog:
        return self._log(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=None,
            action="SEARCH",
            purpose_of_use=purpose_of_use,
            reason=reason,
            break_glass=False,
            session_id=session_id,
            device_id=device_id,
        )

    def log_chart_read(
        self,
        *,
        actor,
        clinic_id,
        patient_id,
        purpose_of_use: str,
        reason: str,
        session_id: str | None = None,
        device_id: str | None = None,
    ) -> AccessLog:
        return self._log(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=patient_id,
            action="CHART_READ",
            purpose_of_use=purpose_of_use,
            reason=reason,
            break_glass=False,
            session_id=session_id,
            device_id=device_id,
        )

    def log_break_glass(
        self,
        *,
        actor,
        clinic_id,
        patient_id,
        purpose_of_use: str,
        reason: str,
        session_id: str | None = None,
        device_id: str | None = None,
    ) -> AccessLog:
        log = self._log(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=patient_id,
            action="BREAK_GLASS",
            purpose_of_use=purpose_of_use,
            reason=reason,
            break_glass=True,
            session_id=session_id,
            device_id=device_id,
        )
        self.event_service.emit(
            event_type="BREAK_GLASS_USED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            emitter="access",
            payload={
                "action": "BREAK_GLASS",
                "purpose_of_use": purpose_of_use,
                "reason": reason,
            },
        )
        return log

    def _log(
        self,
        *,
        actor,
        clinic_id,
        patient_id,
        action: str,
        purpose_of_use: str,
        reason: str,
        break_glass: bool,
        session_id: str | None,
        device_id: str | None,
    ) -> AccessLog:
        if not purpose_of_use or not purpose_of_use.strip():
            raise ValueError("purpose_of_use is required")
        if not reason or not reason.strip():
            raise ValueError("reason is required")

        log = AccessLog(
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            action=action,
            purpose_of_use=purpose_of_use,
            reason=reason,
            break_glass=break_glass,
            session_id=session_id,
            device_id=device_id,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        self.event_service.emit(
            event_type="ACCESS_LOGGED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            emitter="access",
            payload={
                "action": action,
                "purpose_of_use": purpose_of_use,
                "reason": reason,
            },
        )
        return log
