# app/services/event_service.py
import json
from app.models.event_log import EventLog


ALLOWED_EVENT_TYPES = {
    "VISIT_REGISTERED",
    "CONSULTATION_STARTED",
    "LOGIN_FAILED",
    "PATIENT_CREATED",
    "PROVISIONAL_CREATED",
    "IDENTITY_VERIFIED",
    "IDENTITY_MERGED",
    "IDENTITY_SPLIT",
    "IDENTITY_ROLLED_BACK",
    "ENTRY_DRAFTED",
    "ENTRY_SIGNED",
    "ENTRY_AMENDED",
    "ENTRY_VOIDED",
    "LAB_ORDERED",
    "LAB_RESULT_POSTED",
    "ADMISSION_REQUEST_CREATED",
    "ADMISSION_REQUEST_APPROVED",
    "ADMISSION_REQUEST_REJECTED",
    "ADMISSION_REQUEST_CANCELLED",
    "PATIENT_ADMITTED",
    "ADMISSION_CANCELLED",
    "BED_ASSIGNED",
    "BED_TRANSFERRED",
    "BED_STATUS_CHANGED",
    "BED_RELEASED",
    "BED_ACTIVITY_CHANGED",
    "WARD_ACTIVITY_CHANGED",
    "PATIENT_DISCHARGED",
    "TRIAGE_ASSESSMENT_FINALIZED",
    "TRIAGE_ASSESSMENT_SUPERSEDED",
    "TRIAGE_ASSESSMENT_DRAFTED",
    "TRIAGE_ASSESSMENT_SIGNED",
    "PRIORITY_ESCALATED",
    "PRIORITY_DEESCALATED",
    "ACCESS_LOGGED",
    "BREAK_GLASS_USED",
    "OFFLINE_SYNC_APPLIED",
}

EMITTER_EVENT_MAP = {
    "identity": {
        "PATIENT_CREATED",
    "PROVISIONAL_CREATED",
    "IDENTITY_VERIFIED",
    "IDENTITY_MERGED",
    "IDENTITY_SPLIT",
    "IDENTITY_ROLLED_BACK",
    },
    "clinical": {
        "ENTRY_DRAFTED",
        "ENTRY_SIGNED",
        "ENTRY_AMENDED",
        "ENTRY_VOIDED",
        "CONSULTATION_STARTED",
    },
    "lab": {
        "LAB_ORDERED",
        "LAB_RESULT_POSTED",
    },
    "admission": {
        "ADMISSION_REQUEST_CREATED",
        "ADMISSION_REQUEST_APPROVED",
        "ADMISSION_REQUEST_REJECTED",
        "ADMISSION_REQUEST_CANCELLED",
        "PATIENT_ADMITTED",
        "ADMISSION_CANCELLED",
        "PATIENT_DISCHARGED",
    },
    "bed": {
        "BED_ASSIGNED",
        "BED_TRANSFERRED",
        "BED_STATUS_CHANGED",
        "BED_RELEASED",
        "BED_ACTIVITY_CHANGED",
        "WARD_ACTIVITY_CHANGED",
    },
    "triage": {
        "TRIAGE_ASSESSMENT_FINALIZED",
        "TRIAGE_ASSESSMENT_SUPERSEDED",
        "TRIAGE_ASSESSMENT_DRAFTED",
        "TRIAGE_ASSESSMENT_SIGNED",
    },
    "access": {
        "ACCESS_LOGGED",
        "BREAK_GLASS_USED",
    },
    "sync": {
        "OFFLINE_SYNC_APPLIED",
    },
    "clinical_priority_service": {
        "PRIORITY_ESCALATED",
        "PRIORITY_DEESCALATED",
    },
    "visit": {
        "VISIT_REGISTERED",
    },
    "auth": {
        "LOGIN_FAILED",
    },
}


class EventService:
    def __init__(self, db):
        self.db = db

    def emit(
        self,
        *,
        event_type: str,
        actor_id,
        actor_role: str,
        clinic_id,
        payload: dict,
        emitter: str,
        patient_id=None,
    ) -> EventLog:
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Event type not allowed: {event_type}")

        if emitter not in EMITTER_EVENT_MAP:
            raise ValueError(f"Emitter not recognized: {emitter}")

        if event_type not in EMITTER_EVENT_MAP[emitter]:
            raise ValueError(
                f"Emitter {emitter} not permitted to emit {event_type}"
            )

        event = EventLog(
            event_type=event_type,
            actor_id=actor_id,
            actor_role=actor_role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            payload=json.dumps(payload),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def build_event(
        self,
        *,
        event_type: str,
        actor_id,
        actor_role: str,
        clinic_id,
        payload: dict,
        emitter: str,
        patient_id=None,
    ) -> EventLog:
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Event type not allowed: {event_type}")

        if emitter not in EMITTER_EVENT_MAP:
            raise ValueError(f"Emitter not recognized: {emitter}")

        if event_type not in EMITTER_EVENT_MAP[emitter]:
            raise ValueError(
                f"Emitter {emitter} not permitted to emit {event_type}"
            )

        event = EventLog(
            event_type=event_type,
            actor_id=actor_id,
            actor_role=actor_role,
            clinic_id=clinic_id,
            patient_id=patient_id,
            payload=json.dumps(payload),
        )
        self.db.add(event)
        return event
