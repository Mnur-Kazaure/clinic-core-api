# app/schemas/billing.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.enums import BillingEntryType, BillingItemStatus, BillingReasonCode


class BillingChargeCreateRequest(BaseModel):
    code: str | None = None
    amount_minor: int | None = Field(default=None, gt=0)
    description: str = Field(min_length=3)
    reason_code: BillingReasonCode


class BillingPaymentCreateRequest(BaseModel):
    amount_minor: int = Field(gt=0)
    description: str = Field(min_length=3)
    reason_code: BillingReasonCode
    external_ref: str | None = None

    @model_validator(mode="after")
    def validate_manual_payment(self):
        if self.reason_code not in {
            BillingReasonCode.CASH,
            BillingReasonCode.TRANSFER,
            BillingReasonCode.CARD,
        }:
            raise ValueError("Only CASH, TRANSFER, or CARD payment methods are supported")
        if (
            self.reason_code in {BillingReasonCode.TRANSFER, BillingReasonCode.CARD}
            and (self.external_ref is None or len(self.external_ref.strip()) < 3)
        ):
            raise ValueError("Payment reference is required for transfer/card payments")
        return self


class BillingReversalRequest(BaseModel):
    justification: str = Field(min_length=10)
    reason_code: BillingReasonCode


class BillingLedgerEntryResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    visit_id: UUID | None
    admission_id: UUID | None
    entry_type: BillingEntryType
    amount_minor: int
    currency: str
    description: str
    reason_code: BillingReasonCode
    external_ref: str | None
    related_entry_id: UUID | None
    actor_id: UUID
    actor_role: str
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChargeItemPriceResponse(BaseModel):
    id: UUID
    code: str
    name: str
    category: str
    default_amount_minor: int
    currency: str
    active: bool
    display_order: int | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BillingPendingVisitSummary(BaseModel):
    visit_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    currency: str
    pending_items_count: int
    pending_total_minor: int
    latest_created_at: datetime | None = None


class BillingItemResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    visit_id: UUID
    cashier_pay_point_id: UUID | None = None
    charge_catalog_id: UUID | None = None
    charge_code: str | None = None
    item_name: str
    service_type: str
    quantity: int
    unit_price_minor: int
    total_minor: int
    amount_paid_minor: int
    currency: str
    status: BillingItemStatus
    created_by: UUID
    payment_reference: str | None = None
    paid_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BillingPayRequest(BaseModel):
    visit_id: UUID
    billing_item_ids: list[UUID]
    cashier_pay_point_id: UUID | None = None
    payment_method: BillingReasonCode
    external_ref: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_payment_payload(self):
        if not self.billing_item_ids:
            raise ValueError("At least one billing item is required")
        if self.payment_method not in {
            BillingReasonCode.CASH,
            BillingReasonCode.TRANSFER,
            BillingReasonCode.CARD,
        }:
            raise ValueError("Payment method must be CASH, TRANSFER, or CARD")
        if self.payment_method in {
            BillingReasonCode.TRANSFER,
            BillingReasonCode.CARD,
        } and (self.external_ref is None or len(self.external_ref.strip()) < 3):
            raise ValueError("Payment reference is required for transfer/card payments")
        return self


class BillingPaymentDestinationHintResponse(BaseModel):
    billing_item_id: UUID
    item_name: str
    service_type: str
    destination_label: str
    assigned_dispensing_unit_id: UUID | None = None
    assigned_dispensing_unit_name: str | None = None
    readiness_state: str | None = None


class BillingPayResponse(BaseModel):
    receipt_number: str
    receipt_id: UUID | None = None
    visit_id: UUID
    patient_id: UUID
    cashier_pay_point_id: UUID | None = None
    total_paid_minor: int
    currency: str
    payment_method: BillingReasonCode
    paid_item_ids: list[UUID]
    paid_at: datetime
    destination_hints: list[BillingPaymentDestinationHintResponse] = Field(default_factory=list)


class PaymentReceiptSummaryResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    visit_id: UUID
    cashier_pay_point_id: UUID | None = None
    receipt_number: str
    total_amount_minor: int
    currency: str
    payment_method: BillingReasonCode
    external_ref: str | None = None
    collected_by: UUID
    collected_by_name: str | None = None
    occurred_at: datetime


class BillingTransactionRowResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    occurred_at: datetime
    patient_name: str | None = None
    visit_id: UUID
    amount_minor: int
    currency: str
    payment_method: BillingReasonCode
    collected_by_name: str | None = None


class BillingTransactionsResponse(BaseModel):
    data: list[BillingTransactionRowResponse] = Field(default_factory=list)
    total: int
    page: int
    limit: int
    total_amount_minor: int
    currency: str


class PaymentReceiptItemResponse(BaseModel):
    id: UUID
    billing_item_id: UUID
    amount_minor: int
    item_name: str | None = None
    charge_code: str | None = None


class PaymentReceiptDetailResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    visit_id: UUID
    cashier_pay_point_id: UUID | None = None
    receipt_number: str
    total_amount_minor: int
    currency: str
    payment_method: BillingReasonCode
    external_ref: str | None = None
    notes: str | None = None
    collected_by: UUID
    collected_by_name: str | None = None
    occurred_at: datetime
    items: list[PaymentReceiptItemResponse] = Field(default_factory=list)


class ReceiptReprintRequest(BaseModel):
    reason: str | None = Field(default=None, min_length=3)


class ReceiptReprintResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    reprint_log_id: UUID
    reprinted_at: datetime


class ReceiptSequenceResponse(BaseModel):
    clinic_id: UUID
    prefix: str
    padding: int
    last_number: int
    reset_yearly: bool
    current_year: int | None = None


class ReceiptSequenceUpdateRequest(BaseModel):
    prefix: str = Field(min_length=2, max_length=20)
    padding: int = Field(ge=3, le=12)
    reset_yearly: bool = False


class BillingRefundRequest(BaseModel):
    receipt_id: UUID
    billing_item_id: UUID | None = None
    amount_minor: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=3)
    notes: str | None = None


class BillingRefundResponse(BaseModel):
    refund_id: UUID
    receipt_id: UUID
    amount_minor: int
    currency: str
    status: str
    processed_at: datetime
    refunded_item_ids: list[UUID]


class PaymentMethodTotal(BaseModel):
    payment_method: BillingReasonCode
    total_minor: int
    count: int


class BillingDailyReportResponse(BaseModel):
    date: str
    clinic_id: UUID
    total_collected_minor: int
    total_refunded_minor: int
    net_collected_minor: int
    currency: str
    receipts_count: int
    refunds_count: int
    method_breakdown: list[PaymentMethodTotal] = Field(default_factory=list)


class CashierShiftStartRequest(BaseModel):
    opening_float_minor: int = Field(default=0, ge=0)


class CashierShiftEndRequest(BaseModel):
    closing_cash_minor: int | None = Field(default=None, ge=0)
    closing_note: str | None = None


class CashierShiftResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    cashier_id: UUID
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    opening_float_minor: int
    closing_cash_minor: int | None = None
    closing_note: str | None = None

    model_config = ConfigDict(from_attributes=True)
