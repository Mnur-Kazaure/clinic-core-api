from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.enums import BillingReasonCode


class AccountantOverviewResponse(BaseModel):
    date: date
    currency: str
    revenue_today_minor: int
    revenue_this_month_minor: int
    outstanding_bills_minor: int
    refunds_today_minor: int
    net_revenue_minor: int


class DepartmentRevenueItemResponse(BaseModel):
    department_id: UUID | None = None
    department_name: str
    revenue_minor: int
    percentage: float


class PaymentMethodAnalysisItemResponse(BaseModel):
    payment_method: BillingReasonCode
    total_minor: int
    count: int
    percentage: float


class CashierSessionSummaryResponse(BaseModel):
    id: UUID
    cashier_id: UUID
    cashier_name: str | None = None
    status: str
    shift_start: datetime
    shift_end: datetime | None = None
    expected_total_minor: int
    counted_total_minor: int | None = None
    variance_minor: int | None = None
    closing_note: str | None = None
    currency: str


class CashierSessionListResponse(BaseModel):
    data: list[CashierSessionSummaryResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class CashierSessionTransactionResponse(BaseModel):
    id: UUID
    transaction_type: Literal["PAYMENT", "REFUND"]
    occurred_at: datetime
    reference: str
    patient_name: str | None = None
    amount_minor: int
    currency: str
    payment_method: BillingReasonCode | None = None
    actor_name: str | None = None
    note: str | None = None


class CashierSessionDetailResponse(BaseModel):
    session: CashierSessionSummaryResponse
    payments_total_minor: int
    refunds_total_minor: int
    net_total_minor: int
    transactions: list[CashierSessionTransactionResponse] = Field(default_factory=list)


class AccountantRefundRowResponse(BaseModel):
    id: UUID
    receipt_id: UUID
    receipt_number: str
    patient_name: str | None = None
    cashier_name: str | None = None
    amount_minor: int
    currency: str
    reason: str
    status: str
    processed_at: datetime


class AccountantRefundListResponse(BaseModel):
    data: list[AccountantRefundRowResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class RefundReasonResponse(BaseModel):
    id: UUID
    reason_code: str
    description: str | None = None
    is_active: bool


class OutstandingBillRowResponse(BaseModel):
    patient_id: UUID
    patient_name: str | None = None
    outstanding_minor: int
    currency: str
    visits_count: int
    last_visit_id: UUID | None = None


class OutstandingBillListResponse(BaseModel):
    data: list[OutstandingBillRowResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class AccountantAuditFeedRowResponse(BaseModel):
    id: UUID
    event_type: str
    occurred_at: datetime
    actor_name: str | None = None
    amount_minor: int | None = None
    currency: str | None = None
    reference: str | None = None
    detail: str | None = None
    severity: Literal["info", "warning"] = "info"


class AccountantAuditFeedResponse(BaseModel):
    data: list[AccountantAuditFeedRowResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class FraudSignalsResponse(BaseModel):
    date: date
    currency: str
    large_refunds_count: int
    reprints_today_count: int
    open_variances_count: int
    cash_total_today_minor: int
    high_cash_today: bool
    thresholds: dict[str, int]


class CashierSessionReconcileRequest(BaseModel):
    counted_total_minor: int | None = Field(default=None, ge=0)
    closing_note: str | None = Field(default=None, min_length=2)


class CashierSessionReconcileResponse(BaseModel):
    session_id: UUID
    status: str
    counted_total_minor: int | None = None
    variance_minor: int | None = None
    reconciled_at: datetime
