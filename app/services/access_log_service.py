# app/services/access_log_service.py
from fastapi import HTTPException, status

from app.models.access_log import AccessLog
from app.services.event_service import EventService
from app.shared.enums import UserRole, PurposeOfUse


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
        justification: str,
        resource: str,
        session_id: str | None = None,
        device_id: str | None = None,
    ) -> AccessLog:
        return self._log(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=None,
            action="SEARCH",
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource=resource,
            break_glass=False,
            session_id=session_id,
            device_id=device_id,
            commit=True,
        )

    def log_chart_read(
        self,
        *,
        actor,
        clinic_id,
        patient_id,
        purpose_of_use: str,
        justification: str,
        resource: str,
        session_id: str | None = None,
        device_id: str | None = None,
    ) -> AccessLog:
        return self._log(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=patient_id,
            action="CHART_READ",
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource=resource,
            break_glass=False,
            session_id=session_id,
            device_id=device_id,
            commit=True,
        )

    def log_break_glass(
        self,
        *,
        actor,
        clinic_id,
        patient_id,
        purpose_of_use: str,
        justification: str,
        resource: str,
        session_id: str | None = None,
        device_id: str | None = None,
    ) -> AccessLog:
        if actor.role not in {UserRole.DOCTOR, UserRole.CLINIC_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Break-glass access denied",
            )
        purpose_value = self._normalize_purpose(purpose_of_use)
        log = self._log(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=patient_id,
            action="BREAK_GLASS",
            purpose_of_use=purpose_value,
            justification=justification,
            resource=resource,
            break_glass=True,
            session_id=session_id,
            device_id=device_id,
            commit=False,
        )
        self.event_service.build_event(
            event_type="BREAK_GLASS_USED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            emitter="access",
            payload={
                "action": "BREAK_GLASS",
                "purpose_of_use": purpose_value.value,
                "justification": justification,
                "resource": resource,
                "access_log_id": str(log.id),
            },
        )
        self.db.commit()
        self.db.refresh(log)
        return log

    def _log(
        self,
        *,
        actor,
        clinic_id,
        patient_id,
        action: str,
        purpose_of_use: str,
        justification: str,
        resource: str,
        break_glass: bool,
        session_id: str | None,
        device_id: str | None,
        commit: bool,
    ) -> AccessLog:
        purpose_value = self._normalize_purpose(purpose_of_use)
        if not purpose_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="purpose_of_use is required",
            )
        if not justification or not justification.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="justification is required",
            )
        if not resource or not resource.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="resource is required",
            )
        if break_glass and len(justification.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="justification must be at least 10 characters for break-glass",
            )

        log = AccessLog(
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            action=action,
            purpose_of_use=purpose_value,
            justification=justification,
            resource=resource,
            break_glass=break_glass,
            session_id=session_id,
            device_id=device_id,
        )
        self.db.add(log)
        self.db.flush()
        self.event_service.build_event(
            event_type="ACCESS_LOGGED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            emitter="access",
            payload={
                "action": action,
                "purpose_of_use": purpose_value.value,
                "justification": justification,
                "resource": resource,
                "access_log_id": str(log.id),
            },
        )
        if commit:
            self.db.commit()
            self.db.refresh(log)
        return log

    def _normalize_purpose(self, purpose_of_use: str | PurposeOfUse) -> PurposeOfUse:
        if isinstance(purpose_of_use, PurposeOfUse):
            return purpose_of_use
        if not purpose_of_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="purpose_of_use is required",
            )
        try:
            return PurposeOfUse(purpose_of_use)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid purpose_of_use",
            ) from exc
