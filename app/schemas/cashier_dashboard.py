from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import BillingReasonCode, PharmacyExceptionAuthorizationType, PharmacyPrescriptionWorkflowStatus


class CashierDashboardOverviewResponse(BaseModel):
    pending_charges_count: int
    pharmacy_charges_pending: int
    laboratory_charges_pending: int
    paid_today_minor: int
    receipts_today: int
    active_queue: int
    currency: str
    last_updated_at: datetime


class CashierDashboardChargeRowResponse(BaseModel):
    billing_item_id: UUID
    visit_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    source_department_name: str | None = None
    item_name: str
    quantity: int
    amount_minor: int
    currency: str
    service_type: str
    payment_status: str
    cashier_pay_point_id: UUID | None = None
    cashier_pay_point_name: str | None = None
    assigned_dispensing_unit_id: UUID | None = None
    assigned_dispensing_unit_name: str | None = None
    pharmacy_readiness_state: PharmacyPrescriptionWorkflowStatus | None = None
    exception_authorization_type: PharmacyExceptionAuthorizationType | None = None
    destination_hint: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CashierDashboardReceiptRowResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    visit_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    amount_minor: int
    currency: str
    payment_method: BillingReasonCode
    cashier_pay_point_id: UUID | None = None
    cashier_pay_point_name: str | None = None
    collected_by_name: str | None = None
    linked_items: list[str] = Field(default_factory=list)
    destination_hints: list[str] = Field(default_factory=list)
    occurred_at: datetime


class CashierDashboardTransactionRowResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    visit_id: UUID
    patient_id: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    amount_minor: int
    currency: str
    payment_method: BillingReasonCode
    cashier_pay_point_id: UUID | None = None
    cashier_pay_point_name: str | None = None
    collected_by_name: str | None = None
    occurred_at: datetime


class CashierDashboardExceptionRowResponse(BaseModel):
    prescription_id: UUID
    billing_item_id: UUID | None = None
    patient_id: UUID
    patient_name: str | None = None
    patient_mrn: str | None = None
    item_name: str
    assigned_dispensing_unit_name: str | None = None
    exception_authorization_type: PharmacyExceptionAuthorizationType
    payment_status: str
    readiness_state: PharmacyPrescriptionWorkflowStatus
    cashier_pay_point_name: str | None = None
    occurred_at: datetime


class CashierDashboardActivityRowResponse(BaseModel):
    id: str
    action_type: str
    title: str
    detail: str
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    receipt_number: str | None = None
    occurred_at: datetime


class CashierDashboardResponse(BaseModel):
    overview: CashierDashboardOverviewResponse
    pending_charges: list[CashierDashboardChargeRowResponse] = Field(default_factory=list)
    pharmacy_charges: list[CashierDashboardChargeRowResponse] = Field(default_factory=list)
    laboratory_charges: list[CashierDashboardChargeRowResponse] = Field(default_factory=list)
    receipts: list[CashierDashboardReceiptRowResponse] = Field(default_factory=list)
    transactions: list[CashierDashboardTransactionRowResponse] = Field(default_factory=list)
    exceptions_holds: list[CashierDashboardExceptionRowResponse] = Field(default_factory=list)
    activity_audit: list[CashierDashboardActivityRowResponse] = Field(default_factory=list)
