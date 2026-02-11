# app/services/visit/outstanding.py

from __future__ import annotations

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.dispensation import Dispensation
from app.models.lab_request import LabRequest
from app.models.prescription import Prescription
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent
from app.shared.enums import LabRequestStatus, PrescriptionStatus


def compute_outstanding(db: Session, *, visit_id) -> dict:
    """
    Canonical outstanding-work computation for a visit.

    IMPORTANT: This must be the single source of truth for:
    - completion pre-check
    - completion override application
    - any reconcile logic
    """

    pending_labs_count = (
        db.query(LabRequest)
        .filter(
            LabRequest.visit_id == visit_id,
            LabRequest.status == LabRequestStatus.PENDING,
        )
        .count()
    )

    unfulfilled_prescriptions_count = (
        db.query(Prescription)
        .outerjoin(
            PrescriptionFulfillmentEvent,
            and_(
                PrescriptionFulfillmentEvent.prescription_id == Prescription.id,
                PrescriptionFulfillmentEvent.clinic_id == Prescription.clinic_id,
            ),
        )
        .outerjoin(
            Dispensation,
            Dispensation.prescription_id == Prescription.id,
        )
        .filter(
            Prescription.visit_id == visit_id,
            Prescription.status == PrescriptionStatus.ISSUED,
            Dispensation.id.is_(None),
            PrescriptionFulfillmentEvent.id.is_(None),
        )
        .count()
    )

    return {
        "pending_labs_count": pending_labs_count,
        "unfulfilled_prescriptions_count": unfulfilled_prescriptions_count,
        "has_outstanding": (pending_labs_count > 0 or unfulfilled_prescriptions_count > 0),
    }

