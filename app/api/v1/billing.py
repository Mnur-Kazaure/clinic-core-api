# app/api/v1/billing.py
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_db
from app.core.guards.billing_guards import (
    require_billing_charge_role,
    require_billing_payment_role,
    require_billing_reversal_role,
    require_billing_read_role,
)
from app.schemas.billing import (
    BillingChargeCreateRequest,
    BillingPaymentCreateRequest,
    BillingReversalRequest,
    BillingLedgerEntryResponse,
)
from app.services.billing_service import BillingService
from app.services.access_log_service import AccessLogService
from app.shared.enums import PurposeOfUse


router = APIRouter(prefix="/billing", tags=["billing"])


@router.post(
    "/visits/{visit_id}/charges",
    response_model=BillingLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_visit_charge(
    visit_id: UUID,
    payload: BillingChargeCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_charge_role),
):
    service = BillingService(db)
    return service.create_charge_for_visit(
        visit_id=visit_id,
        code=payload.code,
        amount_minor=payload.amount_minor,
        description=payload.description,
        reason_code=payload.reason_code,
        actor=current_user,
    )


@router.post(
    "/patients/{patient_id}/payments",
    response_model=BillingLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_payment(
    patient_id: UUID,
    payload: BillingPaymentCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_payment_role),
):
    service = BillingService(db)
    return service.create_payment_for_patient(
        patient_id=patient_id,
        amount_minor=payload.amount_minor,
        description=payload.description,
        reason_code=payload.reason_code,
        external_ref=payload.external_ref,
        actor=current_user,
    )


@router.post(
    "/ledger/{entry_id}/reverse",
    response_model=BillingLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def reverse_ledger_entry(
    entry_id: UUID,
    payload: BillingReversalRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_reversal_role),
):
    service = BillingService(db)
    return service.reverse_entry(
        entry_id=entry_id,
        justification=payload.justification,
        reason_code=payload.reason_code,
        actor=current_user,
    )


@router.get(
    "/patients/{patient_id}/ledger",
    response_model=list[BillingLedgerEntryResponse],
)
def get_patient_ledger(
    patient_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    if break_glass:
        AccessLogService(db).log_break_glass(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="BILLING_LEDGER",
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="BILLING_LEDGER",
        )
    service = BillingService(db)
    return service.get_ledger_for_patient(
        patient_id=patient_id,
        clinic_id=current_user.clinic_id,
    )


@router.get(
    "/ledger/summary",
    response_model=list[BillingLedgerEntryResponse],
)
def get_ledger_summary(
    limit: int = 100,
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    service = BillingService(db)
    return service.get_ledger_summary(
        clinic_id=current_user.clinic_id,
        limit=limit,
    )
