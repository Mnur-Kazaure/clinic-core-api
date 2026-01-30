# app/services/prescription_service.py
from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session

from app.models.prescription import Prescription
from app.models.visit import Visit
from app.shared.enums import PrescriptionStatus, RecordStatus
from app.shared.exceptions import DomainError
from app.services.event_service import EventService


class PrescriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    # -----------------------------
    # Doctor issues prescription
    # -----------------------------
    def issue_prescription(
        self,
        *,
        consultation,
        visit_id,
        doctor_id,
        payload,
    ) -> Prescription:
        prescription = Prescription(
            id=uuid.uuid4(),
            consultation_id=consultation.id,
            visit_id=visit_id,
            clinic_id=consultation.visit.clinic_id,
            prescribed_by=doctor_id,
            drug_name=payload.drug_name,
            dosage=payload.dosage,
            frequency=payload.frequency,
            duration=payload.duration,
            instructions=payload.instructions,
            status=PrescriptionStatus.ISSUED,
            record_status=RecordStatus.SIGNED,
            signed_at=datetime.now(timezone.utc),
            issued_at=datetime.now(timezone.utc),
        )

        self.db.add(prescription)
        self.db.commit()
        self.db.refresh(prescription)

        self.event_service.emit(
            event_type="ENTRY_SIGNED",
            actor_id=doctor_id,
            actor_role="DOCTOR",
            clinic_id=consultation.visit.clinic_id,
            patient_id=consultation.visit.patient_id,
            emitter="clinical",
            payload={
                "entity": "prescription",
                "prescription_id": str(prescription.id),
                "visit_id": str(visit_id),
            },
        )

        return prescription

    # -----------------------------
    # Pharmacy dispenses medication
    # -----------------------------
    def dispense_prescription(
        self,
        *,
        prescription,
        pharmacist_id,
    ) -> Prescription:
        if prescription.status != PrescriptionStatus.ISSUED:
            raise DomainError("Prescription is not dispensable")

        prescription.status = PrescriptionStatus.DISPENSED
        prescription.dispensed_by = pharmacist_id
        prescription.dispensed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(prescription)

        return prescription

    # -----------------------------
    # Doctor cancels prescription
    # -----------------------------
    def cancel_prescription(
        self,
        *,
        prescription,
        reason: str,
    ) -> Prescription:
        if prescription.status != PrescriptionStatus.ISSUED:
            raise DomainError("Only issued prescriptions may be cancelled")

        prescription.status = PrescriptionStatus.CANCELLED
        prescription.cancelled_at = datetime.now(timezone.utc)
        prescription.record_status = RecordStatus.VOIDED
        prescription.void_reason = reason

        self.db.commit()
        self.db.refresh(prescription)

        visit = (
            self.db.query(Visit)
            .filter(Visit.id == prescription.visit_id)
            .first()
        )

        self.event_service.emit(
            event_type="ENTRY_VOIDED",
            actor_id=prescription.prescribed_by,
            actor_role="DOCTOR",
            clinic_id=prescription.clinic_id,
            patient_id=visit.patient_id if visit else None,
            emitter="clinical",
            payload={
                "entity": "prescription",
                "prescription_id": str(prescription.id),
                "visit_id": str(prescription.visit_id),
                "reason": "cancelled",
            },
        )

        return prescription
