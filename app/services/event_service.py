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
    "LAB_RESULT_ENTERED",
    "LAB_RESULT_SUBMITTED",
    "LAB_RESULT_VERIFIED",
    "LAB_RESULT_RELEASED",
    "LAB_RESULT_AMENDED",
    "LAB_SPECIMEN_REJECTED",
    "LAB_QC_OVERRIDE",
    "LAB_STAFF_ASSIGNMENT_UPDATED",
    "LAB_CONFIGURATION_REQUEST_SUBMITTED",
    "PHARMACY_REFILL_REQUESTED",
    "PHARMACY_REFILL_REVIEWED",
    "PHARMACY_CATALOG_REQUEST_SUBMITTED",
    "PHARMACY_CATALOG_CMD_APPROVED",
    "PHARMACY_CATALOG_CMD_REJECTED",
    "PHARMACY_CATALOG_PRICED",
    "PHARMACY_CATALOG_ACTIVATED",
    "PHARMACY_CATALOG_DEACTIVATED",
    "PHARMACY_CMD_APPROVED",
    "PHARMACY_CMD_REJECTED",
    "PHARMACY_ISSUE_VOUCHER_GENERATED",
    "PHARMACY_ISSUE_DISPATCHED",
    "PHARMACY_ACKNOWLEDGEMENT_RECORDED",
    "PHARMACY_STOCK_ISSUED",
    "PHARMACY_STOCK_RECEIVED",
    "PHARMACY_STORE_STOCK_RECEIVED",
    "PHARMACY_STORE_ADJUSTMENT_RECORDED",
    "STORE_RETURN_REQUESTED",
    "STORE_RETURN_ACCEPTED",
    "STORE_RETURN_REJECTED",
    "STORE_RETURN_RECEIVED",
    "PHARMACY_REASSIGNED",
    "PHARMACY_STAFF_ASSIGNMENT_UPDATED",
    "PHARMACY_PAYMENT_CAPTURED",
    "PHARMACY_ITEM_READY_FOR_DISPENSE",
    "PHARMACY_RECEIPT_CREATED",
    "PHARMACY_PARTIAL_DISPENSED",
    "PHARMACY_FULLY_DISPENSED",
    "PATIENT_ADMITTED",
    "BED_ASSIGNED",
    "BED_RELEASED",
    "BED_TRANSFERRED",
    "PATIENT_DISCHARGED",
    "PRIORITY_ESCALATED",
    "TRIAGE_ASSESSMENT_FINALIZED",
    "TRIAGE_ASSESSMENT_SUPERSEDED",
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
        "LAB_RESULT_ENTERED",
        "LAB_RESULT_SUBMITTED",
        "LAB_RESULT_VERIFIED",
        "LAB_RESULT_RELEASED",
        "LAB_RESULT_AMENDED",
        "LAB_SPECIMEN_REJECTED",
        "LAB_QC_OVERRIDE",
        "LAB_STAFF_ASSIGNMENT_UPDATED",
        "LAB_CONFIGURATION_REQUEST_SUBMITTED",
    },
    "pharmacy": {
        "PHARMACY_REFILL_REQUESTED",
        "PHARMACY_REFILL_REVIEWED",
        "PHARMACY_CATALOG_REQUEST_SUBMITTED",
        "PHARMACY_CATALOG_CMD_APPROVED",
        "PHARMACY_CATALOG_CMD_REJECTED",
        "PHARMACY_CATALOG_PRICED",
        "PHARMACY_CATALOG_ACTIVATED",
        "PHARMACY_CATALOG_DEACTIVATED",
        "PHARMACY_CMD_APPROVED",
        "PHARMACY_CMD_REJECTED",
        "PHARMACY_ISSUE_VOUCHER_GENERATED",
        "PHARMACY_ISSUE_DISPATCHED",
        "PHARMACY_ACKNOWLEDGEMENT_RECORDED",
        "PHARMACY_STOCK_ISSUED",
        "PHARMACY_STOCK_RECEIVED",
        "PHARMACY_STORE_STOCK_RECEIVED",
        "PHARMACY_STORE_ADJUSTMENT_RECORDED",
        "STORE_RETURN_REQUESTED",
        "STORE_RETURN_ACCEPTED",
        "STORE_RETURN_REJECTED",
        "STORE_RETURN_RECEIVED",
        "PHARMACY_REASSIGNED",
        "PHARMACY_STAFF_ASSIGNMENT_UPDATED",
        "PHARMACY_PARTIAL_DISPENSED",
        "PHARMACY_FULLY_DISPENSED",
    },
    "billing_workflow_service": {
        "PHARMACY_PAYMENT_CAPTURED",
        "PHARMACY_ITEM_READY_FOR_DISPENSE",
        "PHARMACY_RECEIPT_CREATED",
    },
    "admission": {
        "PATIENT_ADMITTED",
        "PATIENT_DISCHARGED",
    },
    "triage": {
        "TRIAGE_ASSESSMENT_FINALIZED",
        "TRIAGE_ASSESSMENT_SUPERSEDED",
    },
    "bed": {
        "BED_ASSIGNED",
        "BED_RELEASED",
        "BED_TRANSFERRED",
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
