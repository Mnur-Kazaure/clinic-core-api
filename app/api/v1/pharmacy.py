# app/api/v1/pharmacy.py
from fastapi import APIRouter, Depends, status
from uuid import UUID

from app.core.guards.pharmacy_guards import (
    require_pharmacy_access,
    require_pharmacy_user,
)
from app.core.guards.pharmacy_prescription_guards import require_pharmacy_for_dispense
from app.services.pharmacy_service import PharmacyService
from app.schemas.pharmacy import DispenseCreate, DispenseResponse
from app.schemas.prescription import PrescriptionResponse
from app.core.dependencies import get_db
from app.models.prescription import Prescription
from app.models.dispensation import Dispensation
from app.models.visit import Visit
from app.shared.enums import PrescriptionStatus

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])

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

    prescriptions = q.order_by(Prescription.issued_at.desc()).all()
    _attach_dispensation_status(db, prescriptions, status_filter=status)
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
    return prescription


def _attach_dispensation_status(
    db,
    prescriptions: list[Prescription],
    status_filter: PrescriptionStatus | None = None,
) -> None:
    if not prescriptions:
        return
    ids = [p.id for p in prescriptions]
    dispensations = (
        db.query(Dispensation)
        .filter(Dispensation.prescription_id.in_(ids))
        .all()
    )
    disp_map = {d.prescription_id: d for d in dispensations}

    filtered: list[Prescription] = []
    for prescription in prescriptions:
        dispensation = disp_map.get(prescription.id)
        if dispensation:
            prescription.status = PrescriptionStatus.DISPENSED
            prescription.dispensed_by = dispensation.pharmacist_id
            prescription.dispensed_at = dispensation.created_at
        if status_filter == PrescriptionStatus.DISPENSED and not dispensation:
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
