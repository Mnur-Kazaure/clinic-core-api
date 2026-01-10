# app/services/pharmacy_service.py
from datetime import datetime
import uuid

from app.models.dispensation import Dispensation
from app.models.prescription import Prescription
from app.models.visit import Visit
from app.services.visit.service import VisitService
from app.shared.enums import VisitStatus
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

        # ❌ Safety: prevent double dispense
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
            pharmacist_id=payload.pharmacist_id,
            quantity=payload.quantity,
            created_at=datetime.utcnow(),
        )

        self.db.add(dispensation)
        self.db.commit()
        self.db.refresh(dispensation)

        # 🔁 Phase 2.4 — Auto-complete visit if eligible
        self._try_auto_complete_visit(visit.id)

        return dispensation

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
                Dispensation,
                Dispensation.prescription_id == Prescription.id,
            )
            .filter(
                Prescription.visit_id == visit.id,
                Dispensation.id.is_(None),
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