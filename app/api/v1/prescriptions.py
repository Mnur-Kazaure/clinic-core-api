# app/api/v1/prescriptions.py
from fastapi import APIRouter, Depends, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user



from app.schemas.prescription import (
    PrescriptionCreateRequest,
    PrescriptionDispenseRequest,
    PrescriptionCancelRequest,
    PrescriptionResponse,
)

from app.services.prescription_service import PrescriptionService

from app.core.guards.prescription_guards import (
    require_doctor_for_prescription,
    require_prescription_read_access,
    require_pharmacy_for_dispense,
    require_doctor_for_prescription_cancel,
)

router = APIRouter(
    prefix="/prescriptions",
    tags=["Prescriptions"],
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
