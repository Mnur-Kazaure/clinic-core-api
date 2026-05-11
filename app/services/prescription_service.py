# app/services/prescription_service.py
from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session

from fastapi import HTTPException, status
from app.models.billing_item import BillingItem
from app.models.prescription import Prescription
from app.models.visit import Visit
from app.shared.enums import (
    BillingItemStatus,
    PharmacyPrescriptionWorkflowStatus,
    PrescriptionStatus,
    RecordStatus,
)
from app.shared.exceptions import DomainError
from app.services.event_service import EventService
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.services.pharmacy_service import PharmacyService


class PrescriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    @staticmethod
    def _estimate_prescribed_quantity(payload) -> int:
        explicit_quantity = getattr(payload, "quantity_prescribed", None)
        if explicit_quantity is not None:
            quantity = int(explicit_quantity)
            if quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Prescribed quantity must be greater than zero",
                )
            return quantity

        frequency = str(getattr(payload, "frequency", "") or "").strip().lower()
        duration = str(getattr(payload, "duration", "") or "").strip().lower()

        frequency_map = {
            "once daily": 1,
            "twice daily": 2,
            "three times daily": 3,
            "four times daily": 4,
            "every 6 hours": 4,
            "every 8 hours": 3,
            "every 12 hours": 2,
            "as needed (prn)": 1,
            "before meals": 3,
            "after meals": 3,
            "at bedtime": 1,
            "od": 1,
            "bd": 2,
            "tds": 3,
            "qid": 4,
        }
        duration_map = {
            "3 days": 3,
            "5 days": 5,
            "7 days": 7,
            "10 days": 10,
            "14 days": 14,
            "21 days": 21,
            "28 days": 28,
            "30 days": 30,
            "60 days": 60,
            "90 days": 90,
            "until finished": 7,
            "as directed": 7,
        }

        daily_doses = frequency_map.get(frequency, 1)
        days = duration_map.get(duration, 1)
        return max(daily_doses * days, 1)

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
        issued_at = datetime.now(timezone.utc)
        quantity_prescribed = self._estimate_prescribed_quantity(payload)
        catalog_item, _, _ = PharmacyCatalogGovernanceService(self.db).resolve_operational_item(
            clinic_id=consultation.visit.clinic_id,
            catalog_item_id=getattr(payload, "pharmacy_catalog_item_id", None),
            drug_name=getattr(payload, "drug_name", None),
        )
        prescription = Prescription(
            id=uuid.uuid4(),
            consultation_id=consultation.id,
            visit_id=visit_id,
            clinic_id=consultation.visit.clinic_id,
            prescribed_by=doctor_id,
            pharmacy_catalog_item_id=catalog_item.id,
            drug_name=catalog_item.generic_name,
            dosage=payload.dosage,
            frequency=payload.frequency,
            duration=payload.duration,
            instructions=payload.instructions,
            quantity_prescribed=quantity_prescribed,
            quantity_dispensed_total=0,
            quantity_remaining=quantity_prescribed,
            status=PrescriptionStatus.ISSUED,
            workflow_status=PharmacyPrescriptionWorkflowStatus.ASSIGNED,
            record_status=RecordStatus.DRAFT,
            signed_at=None,
            issued_at=issued_at,
        )

        self.db.add(prescription)
        self.db.flush()

        PharmacyService(self.db).initialize_prescription_workflow(
            prescription=prescription,
            actor=type(
                "PrescriptionActor",
                (),
                {
                    "id": doctor_id,
                    "role": "DOCTOR",
                },
            )(),
            auto_commit=False,
        )

        prescription.record_status = RecordStatus.SIGNED
        prescription.signed_at = issued_at
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

        if prescription.billing_item_id is not None:
            billing_item = (
                self.db.query(BillingItem)
                .filter(BillingItem.id == prescription.billing_item_id)
                .first()
            )
            if billing_item is not None and billing_item.status == BillingItemStatus.PAID:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Paid medication charges cannot be cancelled directly. "
                        "Process refund or billing reversal first."
                    ),
                )
            if billing_item is not None and billing_item.status == BillingItemStatus.PENDING:
                billing_item.status = BillingItemStatus.CANCELLED
                billing_item.paid_at = None
                billing_item.payment_reference = None
                self.db.add(billing_item)

        prescription.status = PrescriptionStatus.CANCELLED
        prescription.workflow_status = PharmacyPrescriptionWorkflowStatus.CANCELLED
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
