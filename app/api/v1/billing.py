# app/api/v1/billing.py
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.encoders import jsonable_encoder

from app.api.v1._sse import build_snapshot_stream
from app.core.database import SessionLocal
from app.core.dependencies import get_db
from app.core.guards.billing_guards import (
    require_billing_catalog_read_role,
    require_billing_charge_role,
    require_billing_payment_role,
    require_billing_refund_role,
    require_billing_reversal_role,
    require_billing_read_role,
    require_billing_shift_role,
    require_receipt_sequence_admin_role,
)
from app.schemas.billing import (
    BillingDailyReportResponse,
    BillingChargeCreateRequest,
    BillingItemResponse,
    BillingPayRequest,
    BillingPayResponse,
    BillingPendingVisitSummary,
    BillingPaymentCreateRequest,
    BillingRefundRequest,
    BillingRefundResponse,
    BillingReversalRequest,
    BillingTransactionsResponse,
    BillingLedgerEntryResponse,
    CashierShiftEndRequest,
    CashierShiftResponse,
    CashierShiftStartRequest,
    ChargeItemPriceResponse,
    PaymentReceiptDetailResponse,
    PaymentReceiptSummaryResponse,
    ReceiptReprintRequest,
    ReceiptReprintResponse,
    ReceiptSequenceResponse,
    ReceiptSequenceUpdateRequest,
)
from app.schemas.cashier_dashboard import CashierDashboardResponse
from app.services.billing_service import BillingService
from app.services.cashier_dashboard_service import CashierDashboardService
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.access_log_service import AccessLogService
from app.shared.enums import BillingReasonCode, PurposeOfUse


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
    "/charge-items",
    response_model=list[ChargeItemPriceResponse],
    status_code=status.HTTP_200_OK,
)
def list_charge_items(
    service_type: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    db=Depends(get_db),
    current_user=Depends(require_billing_catalog_read_role),
):
    return BillingWorkflowService(db).list_charge_items(
        clinic_id=current_user.clinic_id,
        service_type=service_type,
        active_only=active_only,
    )


@router.get(
    "/dashboard",
    response_model=CashierDashboardResponse,
    status_code=status.HTTP_200_OK,
)
def get_cashier_dashboard(
    cashier_pay_point_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=10, le=200),
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return CashierDashboardService(db).get_dashboard(
        clinic_id=current_user.clinic_id,
        cashier_pay_point_id=cashier_pay_point_id,
        search=search,
        limit=limit,
    )


@router.get(
    "/dashboard-stream",
    status_code=status.HTTP_200_OK,
)
async def stream_cashier_dashboard(
    request: Request,
    cashier_pay_point_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=10, le=200),
    current_user=Depends(require_billing_read_role),
):
    def load_snapshot():
        with SessionLocal() as stream_db:
            return CashierDashboardService(stream_db).get_dashboard(
                clinic_id=current_user.clinic_id,
                cashier_pay_point_id=cashier_pay_point_id,
                search=search,
                limit=limit,
            )

    def signature_for(snapshot):
        with SessionLocal() as stream_db:
            return CashierDashboardService(stream_db).snapshot_signature(snapshot)

    return build_snapshot_stream(
        request=request,
        event_name="cashier_dashboard_snapshot",
        load_snapshot=load_snapshot,
        signature_for=signature_for,
        payload_for=lambda snapshot: jsonable_encoder(snapshot),
        event_id_for=lambda snapshot: snapshot["overview"]["last_updated_at"],
    )


@router.get(
    "/pending",
    response_model=list[BillingPendingVisitSummary],
    status_code=status.HTTP_200_OK,
)
def list_pending_billing_visits(
    cashier_pay_point_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=100, ge=1, le=500),
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).list_pending_visit_summaries(
        clinic_id=current_user.clinic_id,
        cashier_pay_point_id=cashier_pay_point_id,
        search=search,
        limit=limit,
    )


@router.get(
    "/items",
    response_model=list[BillingItemResponse],
    status_code=status.HTTP_200_OK,
)
def list_visit_billing_items(
    visit_id: UUID = Query(...),
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).list_visit_items(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
    )


@router.post(
    "/pay",
    response_model=BillingPayResponse,
    status_code=status.HTTP_200_OK,
)
def pay_billing_items(
    payload: BillingPayRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_payment_role),
):
    return BillingWorkflowService(db).pay_billing_items(
        clinic_id=current_user.clinic_id,
        visit_id=payload.visit_id,
        billing_item_ids=payload.billing_item_ids,
        cashier_pay_point_id=payload.cashier_pay_point_id,
        payment_method=payload.payment_method,
        cashier_user=current_user,
        external_ref=payload.external_ref,
        notes=payload.notes,
    )


@router.get(
    "/receipts",
    response_model=list[PaymentReceiptSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def list_receipts(
    search: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).list_receipts(
        clinic_id=current_user.clinic_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get(
    "/transactions",
    response_model=BillingTransactionsResponse,
    status_code=status.HTTP_200_OK,
)
def list_transactions(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    payment_method: BillingReasonCode | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).list_transactions(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
        payment_method=payment_method,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/receipts/{receipt_id}",
    response_model=PaymentReceiptDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_receipt_detail(
    receipt_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).get_receipt_detail(
        clinic_id=current_user.clinic_id,
        receipt_id=receipt_id,
    )


@router.post(
    "/receipts/{receipt_id}/reprint",
    response_model=ReceiptReprintResponse,
    status_code=status.HTTP_200_OK,
)
def reprint_receipt(
    receipt_id: UUID,
    payload: ReceiptReprintRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).log_receipt_reprint(
        clinic_id=current_user.clinic_id,
        receipt_id=receipt_id,
        actor=current_user,
        reason=payload.reason,
    )


@router.get(
    "/receipt-sequence",
    response_model=ReceiptSequenceResponse,
    status_code=status.HTTP_200_OK,
)
def get_receipt_sequence(
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).get_receipt_sequence(
        clinic_id=current_user.clinic_id,
    )


@router.put(
    "/receipt-sequence",
    response_model=ReceiptSequenceResponse,
    status_code=status.HTTP_200_OK,
)
def update_receipt_sequence(
    payload: ReceiptSequenceUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(require_receipt_sequence_admin_role),
):
    return BillingWorkflowService(db).update_receipt_sequence(
        clinic_id=current_user.clinic_id,
        prefix=payload.prefix,
        padding=payload.padding,
        reset_yearly=payload.reset_yearly,
    )


@router.post(
    "/refunds",
    response_model=BillingRefundResponse,
    status_code=status.HTTP_200_OK,
)
def process_refund(
    payload: BillingRefundRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_refund_role),
):
    return BillingWorkflowService(db).process_refund(
        clinic_id=current_user.clinic_id,
        receipt_id=payload.receipt_id,
        actor=current_user,
        reason=payload.reason,
        amount_minor=payload.amount_minor,
        billing_item_id=payload.billing_item_id,
        notes=payload.notes,
    )


@router.get(
    "/daily-report",
    response_model=BillingDailyReportResponse,
    status_code=status.HTTP_200_OK,
)
def get_daily_report(
    for_date: date | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_billing_read_role),
):
    return BillingWorkflowService(db).get_daily_report(
        clinic_id=current_user.clinic_id,
        for_date=for_date or date.today(),
    )


@router.post(
    "/shifts/start",
    response_model=CashierShiftResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_shift(
    payload: CashierShiftStartRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_shift_role),
):
    return BillingWorkflowService(db).start_shift(
        clinic_id=current_user.clinic_id,
        cashier_user=current_user,
        opening_float_minor=payload.opening_float_minor,
    )


@router.post(
    "/shifts/end",
    response_model=CashierShiftResponse,
    status_code=status.HTTP_200_OK,
)
def end_shift(
    payload: CashierShiftEndRequest,
    db=Depends(get_db),
    current_user=Depends(require_billing_shift_role),
):
    return BillingWorkflowService(db).end_shift(
        clinic_id=current_user.clinic_id,
        cashier_user=current_user,
        closing_cash_minor=payload.closing_cash_minor,
        closing_note=payload.closing_note,
    )


@router.get(
    "/shifts/current",
    response_model=CashierShiftResponse | None,
    status_code=status.HTTP_200_OK,
)
def get_current_shift(
    db=Depends(get_db),
    current_user=Depends(require_billing_shift_role),
):
    return BillingWorkflowService(db).get_current_shift(
        clinic_id=current_user.clinic_id,
        cashier_user=current_user,
    )


@router.get(
    "/shifts/{shift_id}/report",
    status_code=status.HTTP_200_OK,
)
def get_shift_report(
    shift_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_billing_shift_role),
):
    return BillingWorkflowService(db).get_shift_report(
        clinic_id=current_user.clinic_id,
        shift_id=shift_id,
        requester=current_user,
    )
