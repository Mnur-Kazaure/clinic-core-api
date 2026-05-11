from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.database import get_db
from app.core.guards.accountant_guards import (
    require_accountant_read_role,
    require_finance_manager_role,
)
from app.schemas.accountant import (
    AccountantAuditFeedResponse,
    AccountantOverviewResponse,
    AccountantRefundListResponse,
    CashierSessionDetailResponse,
    CashierSessionListResponse,
    CashierSessionReconcileRequest,
    CashierSessionReconcileResponse,
    DepartmentRevenueItemResponse,
    FraudSignalsResponse,
    OutstandingBillListResponse,
    PaymentMethodAnalysisItemResponse,
    RefundReasonResponse,
)
from app.schemas.pharmacy_catalog import (
    PharmacyCatalogGovernanceDetailResponse,
    PharmacyCatalogRegistryRowResponse,
    PharmacyPricingConfigUpsertRequest,
)
from app.services.accountant_service import AccountantService
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.shared.enums import BillingReasonCode

router = APIRouter(prefix="/accountant", tags=["Accountant"])


@router.get(
    "/overview",
    response_model=AccountantOverviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_overview(
    for_date: date | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    target_date = for_date or datetime.now(timezone.utc).date()
    return AccountantService(db).get_overview(
        clinic_id=current_user.clinic_id,
        for_date=target_date,
    )


@router.get(
    "/revenue-by-department",
    response_model=list[DepartmentRevenueItemResponse],
    status_code=status.HTTP_200_OK,
)
def get_revenue_by_department(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).list_revenue_by_department(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/payment-methods",
    response_model=list[PaymentMethodAnalysisItemResponse],
    status_code=status.HTTP_200_OK,
)
def get_payment_method_analysis(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).list_payment_methods(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/cashier-sessions",
    response_model=CashierSessionListResponse,
    status_code=status.HTTP_200_OK,
)
def list_cashier_sessions(
    status_filter: str | None = Query(default=None, alias="status"),
    for_date: date | None = Query(default=None, alias="date"),
    cashier_id: UUID | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).list_cashier_sessions(
        clinic_id=current_user.clinic_id,
        status_filter=status_filter,
        for_date=for_date,
        cashier_id=cashier_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/cashier-sessions/{session_id}",
    response_model=CashierSessionDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_cashier_session_detail(
    session_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).get_cashier_session_detail(
        clinic_id=current_user.clinic_id,
        session_id=session_id,
    )


@router.post(
    "/cashier-sessions/{session_id}/reconcile",
    response_model=CashierSessionReconcileResponse,
    status_code=status.HTTP_200_OK,
)
def reconcile_cashier_session(
    session_id: UUID,
    payload: CashierSessionReconcileRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db=Depends(get_db),
    current_user=Depends(require_finance_manager_role),
):
    return AccountantService(db).reconcile_cashier_session(
        clinic_id=current_user.clinic_id,
        session_id=session_id,
        actor=current_user,
        idempotency_key=idempotency_key,
        counted_total_minor=payload.counted_total_minor,
        closing_note=payload.closing_note,
    )


@router.get(
    "/refunds",
    response_model=AccountantRefundListResponse,
    status_code=status.HTTP_200_OK,
)
def list_refunds(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    cashier_id: UUID | None = Query(default=None),
    min_amount_minor: int | None = Query(default=None, ge=0),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).list_refunds(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
        cashier_id=cashier_id,
        min_amount_minor=min_amount_minor,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/refund-reasons",
    response_model=list[RefundReasonResponse],
    status_code=status.HTTP_200_OK,
)
def list_refund_reasons(
    include_inactive: bool = Query(default=False),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).list_refund_reasons(
        clinic_id=current_user.clinic_id,
        include_inactive=include_inactive,
    )


@router.get(
    "/outstanding",
    response_model=OutstandingBillListResponse,
    status_code=status.HTTP_200_OK,
)
def list_outstanding(
    department_id: UUID | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).list_outstanding_bills(
        clinic_id=current_user.clinic_id,
        department_id=department_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/audit-feed",
    response_model=AccountantAuditFeedResponse,
    status_code=status.HTTP_200_OK,
)
def get_audit_feed(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return AccountantService(db).get_audit_feed(
        clinic_id=current_user.clinic_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/fraud-signals",
    response_model=FraudSignalsResponse,
    status_code=status.HTTP_200_OK,
)
def get_fraud_signals(
    for_date: date | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    target_date = for_date or datetime.now(timezone.utc).date()
    return AccountantService(db).get_fraud_signals(
        clinic_id=current_user.clinic_id,
        for_date=target_date,
    )


@router.get("/reports/export", status_code=status.HTTP_200_OK)
def export_report(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    payment_method: BillingReasonCode | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    csv_payload = AccountantService(db).export_csv_report(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
        payment_method=payment_method,
    )
    return Response(
        content=csv_payload,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=accountant-report.csv",
        },
    )


@router.get(
    "/pharmacy-pricing",
    response_model=list[PharmacyCatalogRegistryRowResponse],
    status_code=status.HTTP_200_OK,
)
def list_pharmacy_pricing_queue(
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return PharmacyCatalogGovernanceService(db).list_catalog_items(
        clinic_id=current_user.clinic_id,
    )


@router.post(
    "/pharmacy-pricing/{item_id}",
    response_model=PharmacyCatalogGovernanceDetailResponse,
    status_code=status.HTTP_200_OK,
)
def upsert_pharmacy_pricing(
    item_id: UUID,
    payload: PharmacyPricingConfigUpsertRequest,
    db=Depends(get_db),
    current_user=Depends(require_accountant_read_role),
):
    return PharmacyCatalogGovernanceService(db).configure_pricing(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        item_id=item_id,
        payload=payload,
    )
