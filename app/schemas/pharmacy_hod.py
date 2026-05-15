from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.enums import (
    PharmacyExceptionAuthorizationType,
    PharmacyIssueVoucherStatus,
    PharmacyPrescriptionWorkflowStatus,
    PharmacyRefillRequestStatus,
    PharmacyUnitCategory,
    UserRole,
)
from app.schemas.pharmacy_catalog import PharmacyCatalogRegistryRowResponse


class PharmacyHodDashboardQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class PharmacyHodUnitContextResponse(BaseModel):
    id: UUID
    name: str
    category: PharmacyUnitCategory


class PharmacyHodOverviewMetricResponse(BaseModel):
    pending_prescriptions: int
    ready_to_dispense: int
    awaiting_payment_clearance: int
    stock_risk_items: int
    pending_refill_requests: int
    critical_alerts: int
    delayed_dispense_count: int
    currency: str
    last_updated_at: datetime


class PharmacyHodSystemHealthResponse(BaseModel):
    key: str
    label: str
    status: Literal["OK", "ATTENTION"]
    detail: str


class PharmacyHodUnitSummaryResponse(BaseModel):
    unit_id: UUID
    unit_name: str
    category: PharmacyUnitCategory
    queue_volume: int
    ready_to_dispense: int
    awaiting_payment_clearance: int
    stock_risk: int
    revenue_today_minor: int


class PharmacyHodPayPointPerformanceResponse(BaseModel):
    pay_point_id: UUID
    pay_point_name: str
    transaction_count: int
    revenue_minor: int
    awaiting_clearance_count: int
    currency: str


class PharmacyHodBottleneckItemResponse(BaseModel):
    severity: Literal["info", "warning", "critical"]
    title: str
    detail: str
    unit_id: UUID | None = None
    unit_name: str | None = None


class PharmacyHodUnitOperationResponse(BaseModel):
    unit_id: UUID
    unit_name: str
    category: PharmacyUnitCategory
    queue_volume: int
    ready_to_dispense: int
    awaiting_payment_clearance: int
    staff_on_duty: int
    stock_status: str
    average_dispense_time_minutes: float | None = None
    bottlenecks: list[str] = Field(default_factory=list)


class PharmacyHodDispensingOversightRowResponse(BaseModel):
    prescription_id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    item_name: str
    readiness_state: PharmacyPrescriptionWorkflowStatus
    payment_state: str
    assigned_staff_id: UUID | None = None
    assigned_staff_name: str | None = None
    delay_minutes: int
    exception_authorization_type: PharmacyExceptionAuthorizationType
    issued_at: datetime
    resolved_at: datetime | None = None


class PharmacyHodRefillRequestRowResponse(BaseModel):
    request_id: UUID
    requesting_unit_id: UUID
    requesting_unit_name: str
    requested_by_id: UUID
    requested_by_name: str | None = None
    status: PharmacyRefillRequestStatus
    urgency: str | None = None
    requested_at: datetime
    item_count: int
    total_requested_quantity: int
    total_approved_quantity: int


class PharmacyHodIssueVoucherRowResponse(BaseModel):
    voucher_id: UUID
    voucher_number: str
    store_unit_id: UUID
    store_unit_name: str
    receiving_unit_id: UUID
    receiving_unit_name: str
    status: PharmacyIssueVoucherStatus
    approved_by_name: str | None = None
    issued_by_name: str | None = None
    acknowledged_by_name: str | None = None
    issued_at: datetime
    acknowledged_at: datetime | None = None
    partial_issue: bool
    backorder_pending: bool
    item_count: int


class PharmacyHodStaffSummaryResponse(BaseModel):
    user_id: UUID
    full_name: str | None = None
    email: str
    role: UserRole
    is_active: bool
    assigned_units: list[PharmacyHodUnitContextResponse] = Field(default_factory=list)
    default_unit_id: UUID | None = None
    default_unit_name: str | None = None
    recent_activity_summary: str | None = None
    recent_activity_at: datetime | None = None


class PharmacyHodStaffAssignmentUpdateRequest(BaseModel):
    allowed_unit_ids: list[UUID] = Field(default_factory=list)
    default_unit_id: UUID | None = None


class PharmacyHodUnitAssignmentMemberResponse(BaseModel):
    user_id: UUID
    full_name: str | None = None
    role: UserRole
    is_default: bool
    is_active: bool


class PharmacyHodUnitAssignmentResponse(BaseModel):
    unit_id: UUID
    unit_name: str
    category: PharmacyUnitCategory
    members: list[PharmacyHodUnitAssignmentMemberResponse] = Field(default_factory=list)


class PharmacyHodExceptionOversightRowResponse(BaseModel):
    prescription_id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    exception_type: PharmacyExceptionAuthorizationType
    authorized_by_id: UUID | None = None
    authorized_by_name: str | None = None
    authorized_at: datetime | None = None
    workflow_status: PharmacyPrescriptionWorkflowStatus
    resolution_status: str


class PharmacyHodCriticalAlertRowResponse(BaseModel):
    alert_type: str
    severity: Literal["warning", "critical"]
    title: str
    detail: str
    unit_id: UUID | None = None
    unit_name: str | None = None
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    occurred_at: datetime


class PharmacyHodStockRiskRowResponse(BaseModel):
    unit_id: UUID | None = None
    unit_name: str
    item_id: UUID
    item_name: str
    quantity_on_hand: int
    low_stock_threshold: int
    earliest_expiry_date: date | None = None
    risk_level: Literal["LOW", "CRITICAL", "EXPIRING_SOON", "EXPIRED"]
    detail: str


class PharmacyHodActivityAuditRowResponse(BaseModel):
    id: str
    source_type: str
    action_type: str
    occurred_at: datetime
    actor_id: UUID | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    receipt_number: str | None = None
    summary: str
    detail: str | None = None
    severity: Literal["info", "warning", "critical"] = "info"


class PharmacyHodStaffPerformanceResponse(BaseModel):
    user_id: UUID
    full_name: str | None = None
    role: UserRole
    assigned_units: list[str] = Field(default_factory=list)
    prescriptions_handled: int
    average_dispense_time_minutes: float | None = None
    pending_load: int
    reassignment_count: int
    stock_issue_events: int
    shift_activity_count: int


class PharmacyHodSalesRevenueByUnitResponse(BaseModel):
    unit_id: UUID | None = None
    unit_name: str
    revenue_minor: int


class PharmacyHodSalesRevenueRowResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    occurred_at: datetime
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    visit_id: UUID
    item_name: str
    unit_id: UUID | None = None
    unit_name: str | None = None
    cashier_pay_point_id: UUID | None = None
    cashier_pay_point_name: str | None = None
    amount_minor: int
    currency: str
    cashier_name: str | None = None


class PharmacyHodSalesRevenueResponse(BaseModel):
    total_revenue_minor: int
    receipt_count: int
    paid_item_count: int
    currency: str
    revenue_by_unit: list[PharmacyHodSalesRevenueByUnitResponse] = Field(default_factory=list)
    rows: list[PharmacyHodSalesRevenueRowResponse] = Field(default_factory=list)


class PharmacyHodReceiptRegisterRowResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    occurred_at: datetime
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    visit_id: UUID
    amount_minor: int
    currency: str
    cashier_name: str | None = None
    cashier_pay_point_name: str | None = None
    unit_names: list[str] = Field(default_factory=list)
    linked_items: list[str] = Field(default_factory=list)


class PharmacyHodReportsAnalyticsResponse(BaseModel):
    revenue_by_unit: list[PharmacyHodSalesRevenueByUnitResponse] = Field(default_factory=list)
    revenue_by_pay_point: list[PharmacyHodPayPointPerformanceResponse] = Field(default_factory=list)
    refill_frequency_by_unit: list[PharmacyHodSalesRevenueByUnitResponse] = Field(default_factory=list)
    dispense_turnaround_by_unit: list[PharmacyHodSalesRevenueByUnitResponse] = Field(default_factory=list)
    stock_risk_counts: list[dict[str, int | str]] = Field(default_factory=list)


class PharmacyHodDashboardResponse(BaseModel):
    generated_at: datetime
    start_date: date
    end_date: date
    overview: PharmacyHodOverviewMetricResponse
    system_health: list[PharmacyHodSystemHealthResponse] = Field(default_factory=list)
    unit_summary: list[PharmacyHodUnitSummaryResponse] = Field(default_factory=list)
    pay_point_performance: list[PharmacyHodPayPointPerformanceResponse] = Field(default_factory=list)
    bottlenecks: list[PharmacyHodBottleneckItemResponse] = Field(default_factory=list)
    unit_operations: list[PharmacyHodUnitOperationResponse] = Field(default_factory=list)
    dispensing_oversight: list[PharmacyHodDispensingOversightRowResponse] = Field(default_factory=list)
    store_supply: list[PharmacyHodRefillRequestRowResponse] = Field(default_factory=list)
    issue_vouchers: list[PharmacyHodIssueVoucherRowResponse] = Field(default_factory=list)
    staff_control: list[PharmacyHodStaffSummaryResponse] = Field(default_factory=list)
    unit_assignment: list[PharmacyHodUnitAssignmentResponse] = Field(default_factory=list)
    pending_approvals: list[PharmacyHodRefillRequestRowResponse] = Field(default_factory=list)
    exception_oversight: list[PharmacyHodExceptionOversightRowResponse] = Field(default_factory=list)
    critical_alerts: list[PharmacyHodCriticalAlertRowResponse] = Field(default_factory=list)
    stock_risk_expiry: list[PharmacyHodStockRiskRowResponse] = Field(default_factory=list)
    activity_audit: list[PharmacyHodActivityAuditRowResponse] = Field(default_factory=list)
    staff_performance: list[PharmacyHodStaffPerformanceResponse] = Field(default_factory=list)
    sales_revenue: PharmacyHodSalesRevenueResponse
    receipt_register: list[PharmacyHodReceiptRegisterRowResponse] = Field(default_factory=list)
    reports_analytics: PharmacyHodReportsAnalyticsResponse
    configuration_requests: list[PharmacyCatalogRegistryRowResponse] = Field(default_factory=list)
    configuration_requests_enabled: bool = True
