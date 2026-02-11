# app/services/pharmacy_service.py
from datetime import datetime, timezone
import uuid

from sqlalchemy.exc import IntegrityError

from app.models.dispensation import Dispensation
from app.models.prescription import Prescription
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent
from app.models.visit import Visit
from app.services.visit.service import VisitService
from app.shared.enums import (
    PrescriptionFulfillmentType,
    PrescriptionStatus,
    VisitStatus,
)
from app.core.system_actor import SystemUser


class PharmacyService:
    def __init__(self, db):
        self.db = db

    def dispense(self, visit, payload):
        prescription = (
            self.db.query(Prescription)
            .filter(Prescription.visit_id == visit.id)
            .first()
        )

        if not prescription:
            raise ValueError("No prescription found for visit")

        return self.dispense_prescription(prescription, payload)

    def dispense_prescription(self, prescription, payload):
        existing_event = (
            self.db.query(PrescriptionFulfillmentEvent)
            .filter(
                PrescriptionFulfillmentEvent.prescription_id == prescription.id,
                PrescriptionFulfillmentEvent.clinic_id == prescription.clinic_id,
            )
            .first()
        )
        if existing_event:
            raise ValueError("Prescription already fulfilled")

        existing = (
            self.db.query(Dispensation)
            .filter(Dispensation.prescription_id == prescription.id)
            .first()
        )
        if existing:
            raise ValueError("Prescription already dispensed")

        dispensation = Dispensation(
            id=uuid.uuid4(),
            prescription_id=prescription.id,
            clinic_id=prescription.clinic_id,
            pharmacist_id=payload.pharmacist_id,
            quantity=payload.quantity,
            created_at=datetime.now(timezone.utc),
        )

        fulfillment_event = PrescriptionFulfillmentEvent(
            id=uuid.uuid4(),
            clinic_id=prescription.clinic_id,
            prescription_id=prescription.id,
            actor_id=payload.pharmacist_id,
            fulfillment_type=PrescriptionFulfillmentType.DISPENSED_IN_HOUSE,
            quantity=payload.quantity,
            occurred_at=datetime.now(timezone.utc),
        )

        self.db.add_all([dispensation, fulfillment_event])
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Prescription already fulfilled") from None
        self.db.refresh(dispensation)

        self._try_auto_complete_visit(prescription.visit_id)

        return dispensation

    def mark_dispensed_external(self, prescription, *, actor_id, note: str | None = None):
        existing_event = (
            self.db.query(PrescriptionFulfillmentEvent)
            .filter(
                PrescriptionFulfillmentEvent.prescription_id == prescription.id,
                PrescriptionFulfillmentEvent.clinic_id == prescription.clinic_id,
            )
            .first()
        )
        if existing_event:
            raise ValueError("Prescription already fulfilled")

        fulfillment_event = PrescriptionFulfillmentEvent(
            id=uuid.uuid4(),
            clinic_id=prescription.clinic_id,
            prescription_id=prescription.id,
            actor_id=actor_id,
            fulfillment_type=PrescriptionFulfillmentType.DISPENSED_EXTERNAL,
            quantity=None,
            note=note,
            occurred_at=datetime.now(timezone.utc),
        )

        self.db.add(fulfillment_event)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Prescription already fulfilled") from None
        self.db.refresh(fulfillment_event)

        self._try_auto_complete_visit(prescription.visit_id)

        return fulfillment_event

    # Public recheck for dashboard refresh
    def recheck_auto_complete_visit(self, visit_id):
        self._try_auto_complete_visit(visit_id)
        return (
            self.db.query(Visit)
            .filter(Visit.id == visit_id)
            .first()
        )

    # 🔒 INTERNAL ONLY — no router access
    def _try_auto_complete_visit(self, visit_id):
        visit = (
            self.db.query(Visit)
            .filter(Visit.id == visit_id)
            .first()
        )

        if not visit:
            return

        # Must be pharmacy stage
        if visit.status != VisitStatus.PHARMACY_PENDING:
            return

        # Are there any prescriptions without dispensation?
        undispensed = (
            self.db.query(Prescription)
            .outerjoin(
                PrescriptionFulfillmentEvent,
                (PrescriptionFulfillmentEvent.prescription_id == Prescription.id)
                & (PrescriptionFulfillmentEvent.clinic_id == Prescription.clinic_id),
            )
            .outerjoin(
                Dispensation,
                Dispensation.prescription_id == Prescription.id,
            )
            .filter(
                Prescription.visit_id == visit.id,
                Prescription.status == PrescriptionStatus.ISSUED,
                Dispensation.id.is_(None),
                PrescriptionFulfillmentEvent.id.is_(None),
            )
            .count()
        )

        if undispensed > 0:
            return

        # ✅ Auto-complete visit as SYSTEM
        VisitService(self.db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.COMPLETED,
            user=SystemUser,
        )
