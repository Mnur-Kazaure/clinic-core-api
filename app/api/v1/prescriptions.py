# app/api/v1/prescriptions.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user



from app.schemas.prescription import (
    PrescriptionCreateRequest,
    PrescriptionDispenseRequest,
    PrescriptionCancelRequest,
    PrescriptionResponse,
)
from app.schemas.pharmacy_catalog import PharmacyActiveCatalogItemResponse

from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.services.prescription_service import PrescriptionService

from app.core.guards.prescription_guards import (
    require_doctor_for_prescription,
    require_prescription_read_access,
    require_pharmacy_for_dispense,
    require_doctor_for_prescription_cancel,
)
from app.shared.enums import UserRole

router = APIRouter(
    prefix="/prescriptions",
    tags=["Prescriptions"],
)


@router.get(
    "/catalog/active",
    response_model=list[PharmacyActiveCatalogItemResponse],
    status_code=status.HTTP_200_OK,
)
def list_active_catalog_items(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if str(current_user.role) != UserRole.DOCTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
        )
    return PharmacyCatalogGovernanceService(db).list_active_catalog_items(
        clinic_id=current_user.clinic_id
    )

# ---------------------------------------------------------
# 1️⃣ Issue Prescription (Doctor-only)
# ---------------------------------------------------------
@router.post(
    "",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_prescription(
    payload: PrescriptionCreateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    consultation=Depends(require_doctor_for_prescription),
):
    """
    Clinical intent only.
    No Visit or Consultation mutation.
    """
    service = PrescriptionService(db)

    prescription = service.issue_prescription(
        consultation=consultation,
        visit_id=consultation.visit_id,
        doctor_id=current_user.id,
        payload=payload,
    )

    return prescription


# ---------------------------------------------------------
# 2️⃣ Get Prescription by ID (Read-only)
# ---------------------------------------------------------
@router.get(
    "/{prescription_id}",
    response_model=PrescriptionResponse,
)
def get_prescription(
    prescription=Depends(require_prescription_read_access),
):
    """
    Read-only access.
    Guard enforces authority.
    """
    return prescription


# ---------------------------------------------------------
# 4️⃣ Cancel Prescription (Doctor-only)
# ---------------------------------------------------------
@router.post(
    "/{prescription_id}/cancel",
    response_model=PrescriptionResponse,
)
def cancel_prescription(
    payload: PrescriptionCancelRequest,
    prescription=Depends(require_doctor_for_prescription_cancel),
    db=Depends(get_db),
):
    """
    Explicit cancellation.
    ISSUED-only.
    """
    service = PrescriptionService(db)

    cancelled = service.cancel_prescription(
        prescription=prescription,
        reason=payload.reason,
    )

    return cancelled
