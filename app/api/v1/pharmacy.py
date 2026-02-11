# app/api/v1/pharmacy.py
from fastapi import APIRouter, Depends, status, HTTPException
from uuid import UUID

from app.core.guards.pharmacy_guards import (
    require_pharmacy_access,
    require_pharmacy_user,
)
from app.core.guards.pharmacy_prescription_guards import require_pharmacy_for_dispense
from app.services.pharmacy_service import PharmacyService
from app.schemas.pharmacy import (
    DispenseCreate,
    DispenseResponse,
    ExternalFulfillCreate,
    PrescriptionFulfillmentResponse,
)
from app.schemas.prescription import PrescriptionResponse
from app.core.dependencies import get_db
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.patient_mrn import PatientMRN
from app.models.prescription import Prescription
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent
from app.models.dispensation import Dispensation
from app.models.user import User
from app.models.visit import Visit
from app.shared.enums import (
    PrescriptionFulfillmentType,
    PrescriptionStatus,
    MRNStatus,
    VisitStatus,
)

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])

# -----------------------------
# Helpers
# -----------------------------

def _resolve_canonical_patient_id(
    db,
    *,
    clinic_id: UUID,
    patient_id: UUID,
) -> UUID:
    visited = set()
    current = patient_id
    for _ in range(10):
        if current in visited:
            return patient_id
        visited.add(current)
        mapping = (
            db.query(PatientIdentityMap)
            .filter(
                PatientIdentityMap.clinic_id == clinic_id,
                PatientIdentityMap.from_patient_id == current,
            )
            .first()
        )
        if not mapping:
            return current
        revoked = (
            db.query(IdentityMapRevocation)
            .filter(
                IdentityMapRevocation.clinic_id == clinic_id,
                IdentityMapRevocation.map_id == mapping.id,
            )
            .first()
        )
        if revoked:
            return current
        current = mapping.to_patient_id
    return patient_id


def _attach_patient_info(
    db,
    *,
    clinic_id: UUID,
    prescriptions: list[Prescription],
) -> None:
    if not prescriptions:
        return
    visit_ids = {prescription.visit_id for prescription in prescriptions}
    visits = db.query(Visit).filter(Visit.id.in_(visit_ids)).all()
    visit_map = {visit.id: visit for visit in visits}
    patient_ids = {visit.patient_id for visit in visits}
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    patient_name_map = {patient.id: patient.full_name for patient in patients}
    canonical_map = {
        patient_id: _resolve_canonical_patient_id(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        for patient_id in patient_ids
    }
    canonical_ids = set(canonical_map.values())
    mrns = (
        db.query(PatientMRN.patient_id, PatientMRN.mrn)
        .filter(
            PatientMRN.patient_id.in_(canonical_ids),
            PatientMRN.clinic_id == clinic_id,
            PatientMRN.status == MRNStatus.ACTIVE,
        )
        .all()
    )
    mrn_map = {patient_id: mrn for patient_id, mrn in mrns}
    prescriber_ids = {prescription.prescribed_by for prescription in prescriptions}
    dispenser_ids = {
        prescription.dispensed_by
        for prescription in prescriptions
        if prescription.dispensed_by
    }
    user_ids = prescriber_ids | dispenser_ids
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {user.id: user for user in users}

    for prescription in prescriptions:
        visit = visit_map.get(prescription.visit_id)
        if not visit:
            prescription.patient_id = None
            prescription.patient_name = None
            prescription.patient_mrn = None
            prescription.prescribed_by_name = None
            prescription.prescribed_by_role = None
            prescription.dispensed_by_name = None
            prescription.dispensed_by_role = None
            continue
        prescription.patient_id = visit.patient_id
        prescription.patient_name = patient_name_map.get(visit.patient_id)
        canonical_id = canonical_map.get(visit.patient_id, visit.patient_id)
        prescription.patient_mrn = mrn_map.get(canonical_id)
        prescriber = user_map.get(prescription.prescribed_by)
        prescription.prescribed_by_name = (
            prescriber.full_name if prescriber else None
        )
        prescription.prescribed_by_role = (
            prescriber.role if prescriber else None
        )
        dispenser = (
            user_map.get(prescription.dispensed_by)
            if prescription.dispensed_by
            else None
        )
        prescription.dispensed_by_name = (
            dispenser.full_name if dispenser else None
        )
        prescription.dispensed_by_role = (
            dispenser.role if dispenser else None
        )

# GET /pharmacy/prescriptions?status=ISSUED
@router.get(
    "/prescriptions",
    response_model=list[PrescriptionResponse],
    status_code=status.HTTP_200_OK,
)
def list_prescriptions(
    status: PrescriptionStatus | None = None,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    q = (
        db.query(Prescription)
        .join(Visit, Prescription.visit_id == Visit.id)
        .filter(Visit.clinic_id == current_user.clinic_id)
    )

    if status is not None and status != PrescriptionStatus.DISPENSED:
        q = q.filter(Prescription.status == status)
        if status == PrescriptionStatus.ISSUED:
            # Pharmacy queue must not depend on visit.status to avoid trapping ops when
            # visits are completed via override completion.
            q = q.filter(Visit.status != VisitStatus.CANCELLED)

    prescriptions = q.order_by(Prescription.issued_at.desc()).all()
    _attach_dispensation_status(db, prescriptions, status_filter=status)
    _attach_patient_info(
        db,
        clinic_id=current_user.clinic_id,
        prescriptions=prescriptions,
    )
    return prescriptions


@router.get(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
)
def get_prescription(
    prescription_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    prescription = (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id)
        .first()
    )

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    visit = (
        db.query(Visit)
        .filter(Visit.id == prescription.visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    _attach_dispensation_status(db, [prescription])
    _attach_patient_info(
        db,
        clinic_id=current_user.clinic_id,
        prescriptions=[prescription],
    )
    return prescription


def _attach_dispensation_status(
    db,
    prescriptions: list[Prescription],
    status_filter: PrescriptionStatus | None = None,
) -> None:
    if not prescriptions:
        return
    ids = [p.id for p in prescriptions]
    fulfillment_events = (
        db.query(PrescriptionFulfillmentEvent)
        .filter(PrescriptionFulfillmentEvent.prescription_id.in_(ids))
        .all()
    )
    event_map = {e.prescription_id: e for e in fulfillment_events}
    dispensations = (
        db.query(Dispensation)
        .filter(Dispensation.prescription_id.in_(ids))
        .all()
    )
    disp_map = {d.prescription_id: d for d in dispensations}

    filtered: list[Prescription] = []
    for prescription in prescriptions:
        fulfillment_event = event_map.get(prescription.id)
        dispensation = disp_map.get(prescription.id)
        if fulfillment_event:
            prescription.status = PrescriptionStatus.DISPENSED
            prescription.dispensed_by = fulfillment_event.actor_id
            prescription.dispensed_at = fulfillment_event.occurred_at
            prescription.fulfillment_type = fulfillment_event.fulfillment_type
            prescription.fulfillment_note = fulfillment_event.note
        elif dispensation:
            # Legacy fallback (older rows may have Dispensation but no fulfillment event).
            prescription.status = PrescriptionStatus.DISPENSED
            prescription.dispensed_by = dispensation.pharmacist_id
            prescription.dispensed_at = dispensation.created_at
            prescription.fulfillment_type = (
                PrescriptionFulfillmentType.DISPENSED_IN_HOUSE
            )
            prescription.fulfillment_note = None

        if status_filter == PrescriptionStatus.ISSUED and (
            fulfillment_event or dispensation
        ):
            # Do not show already-fulfilled prescriptions in the ISSUED queue.
            continue
        if (
            status_filter == PrescriptionStatus.DISPENSED
            and not fulfillment_event
            and not dispensation
        ):
            continue
        filtered.append(prescription)

    prescriptions[:] = filtered


# api/pharmacy/visits/{visit_id}/dispense (This endpoint triger auto-complation)
@router.post(
    "/{visit_id}/dispense",
    response_model=DispenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def dispense_medication(
    visit_id: UUID,
    payload: DispenseCreate,
    visit=Depends(require_pharmacy_access),  # 🔒 Guard enforced here
    db=Depends(get_db),
):
    service = PharmacyService(db)

    dispense = service.dispense(
        visit=visit,
        payload=payload,
    )

    return dispense


# POST /pharmacy/prescriptions/{prescription_id}/dispense
@router.post(
    "/prescriptions/{prescription_id}/dispense",
    response_model=DispenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def dispense_prescription(
    prescription_id: UUID,
    payload: DispenseCreate,
    prescription=Depends(require_pharmacy_for_dispense),
    db=Depends(get_db),
):
    service = PharmacyService(db)
    dispense = service.dispense_prescription(prescription, payload)
    return dispense


@router.post(
    "/prescriptions/{prescription_id}/fulfill-external",
    response_model=PrescriptionFulfillmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def fulfill_prescription_external(
    prescription_id: UUID,
    payload: ExternalFulfillCreate,
    prescription=Depends(require_pharmacy_for_dispense),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    """
    Mark a prescription as fulfilled outside the clinic (e.g., out of stock).
    This writes an append-only fulfillment event and participates in visit auto-completion.
    """
    service = PharmacyService(db)
    event = service.mark_dispensed_external(
        prescription,
        actor_id=current_user.id,
        note=payload.note,
    )
    return event
