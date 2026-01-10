# app/services/prescription_service.py
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.models.prescription import Prescription
from app.shared.enums import PrescriptionStatus
from app.shared.exceptions import DomainError


class PrescriptionService:
    def __init__(self, db: Session):
        self.db = db

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
            prescribed_by=doctor_id,
            drug_name=payload.drug_name,
            dosage=payload.dosage,
            frequency=payload.frequency,
            duration=payload.duration,
            instructions=payload.instructions,
            status=PrescriptionStatus.ISSUED,
            issued_at=datetime.utcnow(),
        )

        self.db.add(prescription)
        self.db.commit()
        self.db.refresh(prescription)

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
        prescription.dispensed_at = datetime.utcnow()

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
    ) -> Prescription:
        if prescription.status != PrescriptionStatus.ISSUED:
            raise DomainError("Only issued prescriptions may be cancelled")

        prescription.status = PrescriptionStatus.CANCELLED
        prescription.cancelled_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(prescription)

        return prescription