from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pharmacy_supply import PharmacyReturnRequestResponse
from app.shared.enums import (
    PharmacyIssueVoucherStatus,
    PharmacyRefillRequestStatus,
    PharmacyRequestType,
    PharmacyInventoryClassification,
    PharmacyInventoryTrackingMode,
)


class PharmacyStoreDashboardQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    store_unit_id: UUID | None = None


class PharmacyStoreOverviewResponse(BaseModel):
    pending_approved_requests: int
    items_awaiting_issue: int
    pending_receiving_acknowledgements: int
    pending_return_reviews: int
    low_stock_items: int
    expiring_soon_items: int
    stock_adjustments_pending: int
    currency: str
    last_updated_at: datetime


class PharmacyStoreOperationalSummaryRowResponse(BaseModel):
    label: str
    count: int
    detail: str | None = None
    severity: Literal["info", "warning", "critical"] = "info"


class PharmacyStoreInventoryRowResponse(BaseModel):
    inventory_item_id: UUID
    item_name: str
    dosage_form: str
    strength: str | None = None
    classification: PharmacyInventoryClassification
    tracking_mode: PharmacyInventoryTrackingMode
    requires_expiry: bool
    category: str
    unit_of_measure: str
    batch_number: str | None = None
    expiry_date: date | None = None
    quantity_on_hand: int
    reserved_quantity: int
    available_quantity: int
    low_stock_threshold: int
    stock_status: str
    currency: str
    location_label: str | None = None
    can_issue: bool


class PharmacyStoreRequestItemResponse(BaseModel):
    refill_request_item_id: UUID
    inventory_item_id: UUID
    inventory_item_name: str
    requested_quantity: int
    approved_quantity: int
    reserved_quantity: int
    issued_quantity: int
    received_quantity: int
    pending_quantity: int
    backorder_quantity: int


class PharmacyStoreApprovedRequestRowResponse(BaseModel):
    request_id: UUID
    request_number: str
    requesting_unit_id: UUID
    requesting_unit_name: str
    request_type: PharmacyRequestType
    requested_at: datetime
    approved_by_name: str | None = None
    priority: Literal["ROUTINE", "URGENT", "EMERGENCY"]
    status: PharmacyRefillRequestStatus
    item_count: int
    total_requested_quantity: int
    total_reserved_quantity: int
    total_pending_quantity: int
    backorder_pending: bool
    waiting_minutes: int
    requester_timeline: list[str] = Field(default_factory=list)
    items: list[PharmacyStoreRequestItemResponse] = Field(default_factory=list)


class PharmacyStoreIssueVoucherItemResponse(BaseModel):
    voucher_item_id: UUID
    inventory_item_id: UUID
    inventory_item_name: str
    requested_quantity: int
    reserved_quantity: int
    issued_quantity: int
    received_quantity: int
    pending_quantity: int
    batch_number: str
    expiry_date: date | None = None


class PharmacyStoreIssueVoucherRowResponse(BaseModel):
    voucher_id: UUID
    voucher_number: str
    receiving_unit_id: UUID
    receiving_unit_name: str
    issue_date: datetime | None = None
    prepared_at: datetime | None = None
    dispatched_at: datetime | None = None
    prepared_by_name: str | None = None
    issued_by_name: str | None = None
    approved_by_name: str | None = None
    received_by_name: str | None = None
    status: PharmacyIssueVoucherStatus
    partial_issue: bool
    pending_quantity: int
    awaiting_acknowledgement: bool
    discrepancy_pending: bool
    items: list[PharmacyStoreIssueVoucherItemResponse] = Field(default_factory=list)


class PharmacyStoreMovementRowResponse(BaseModel):
    movement_id: UUID
    occurred_at: datetime
    movement_type: str
    item_name: str
    batch_number: str | None = None
    quantity_delta: int
    source_label: str | None = None
    destination_label: str | None = None
    actor_name: str | None = None
    reference_number: str | None = None
    reference_type: str | None = None


class PharmacyStoreExpiryRiskRowResponse(BaseModel):
    inventory_item_id: UUID
    item_name: str
    batch_number: str
    expiry_date: date | None = None
    quantity_on_hand: int
    risk_level: Literal["LOW_STOCK", "EXPIRING_SOON", "EXPIRED"]
    recommended_action: str


class PharmacyStoreAdjustmentRowResponse(BaseModel):
    movement_id: UUID
    occurred_at: datetime
    item_name: str
    batch_number: str | None = None
    quantity_delta: int
    actor_name: str | None = None
    reason: str | None = None
    reference_number: str | None = None


class PharmacyStoreActivityRowResponse(BaseModel):
    id: str
    occurred_at: datetime
    action_type: str
    summary: str
    detail: str | None = None
    item_name: str | None = None
    unit_name: str | None = None
    voucher_number: str | None = None
    request_number: str | None = None
    actor_name: str | None = None
    severity: Literal["info", "warning", "critical"] = "info"


class PharmacyStoreTrendRowResponse(BaseModel):
    label: str
    value: int


class PharmacyStoreReportsAnalyticsResponse(BaseModel):
    stock_received_by_period: int
    stock_issued_by_period: int
    issue_volume_by_unit: list[PharmacyStoreTrendRowResponse] = Field(default_factory=list)
    top_consumed_items: list[PharmacyStoreTrendRowResponse] = Field(default_factory=list)
    stock_out_frequency: list[PharmacyStoreTrendRowResponse] = Field(default_factory=list)
    expiry_trend: list[PharmacyStoreTrendRowResponse] = Field(default_factory=list)
    backorder_trend: list[PharmacyStoreTrendRowResponse] = Field(default_factory=list)
    adjustment_trend: list[PharmacyStoreTrendRowResponse] = Field(default_factory=list)


class PharmacyStoreDashboardResponse(BaseModel):
    generated_at: datetime
    start_date: date
    end_date: date
    store_unit_id: UUID
    store_unit_name: str
    currency: str
    overview: PharmacyStoreOverviewResponse
    supply_workload: list[PharmacyStoreOperationalSummaryRowResponse] = Field(default_factory=list)
    stock_risk_summary: list[PharmacyStoreOperationalSummaryRowResponse] = Field(default_factory=list)
    dispatch_status: list[PharmacyStoreOperationalSummaryRowResponse] = Field(default_factory=list)
    top_consuming_units: list[PharmacyStoreTrendRowResponse] = Field(default_factory=list)
    inventory: list[PharmacyStoreInventoryRowResponse] = Field(default_factory=list)
    department_requests: list[PharmacyStoreApprovedRequestRowResponse] = Field(default_factory=list)
    approved_requests: list[PharmacyStoreApprovedRequestRowResponse] = Field(default_factory=list)
    issue_vouchers: list[PharmacyStoreIssueVoucherRowResponse] = Field(default_factory=list)
    dispatch_receiving: list[PharmacyStoreIssueVoucherRowResponse] = Field(default_factory=list)
    return_requests: list[PharmacyReturnRequestResponse] = Field(default_factory=list)
    movement_history: list[PharmacyStoreMovementRowResponse] = Field(default_factory=list)
    expiry_low_stock: list[PharmacyStoreExpiryRiskRowResponse] = Field(default_factory=list)
    adjustments_reconciliation: list[PharmacyStoreAdjustmentRowResponse] = Field(default_factory=list)
    activity_audit: list[PharmacyStoreActivityRowResponse] = Field(default_factory=list)
    reports_analytics: PharmacyStoreReportsAnalyticsResponse


class PharmacyStoreReceiveStockRequest(BaseModel):
    store_unit_id: UUID
    inventory_item_id: UUID
    batch_number: str = Field(min_length=1, max_length=80)
    expiry_date: date | None = None
    quantity_received: int = Field(gt=0)
    unit_cost_minor: int | None = Field(default=None, ge=0)
    source_reference_note: str | None = Field(default=None, max_length=255)


class PharmacyStoreAdjustmentRequest(BaseModel):
    store_unit_id: UUID
    inventory_item_id: UUID
    batch_number: str | None = Field(default=None, max_length=80)
    expiry_date: date | None = None
    quantity_delta: int
    reason: str = Field(min_length=3, max_length=255)


class PharmacyStoreStockActionResponse(BaseModel):
    inventory_item_id: UUID
    item_name: str
    batch_number: str | None = None
    quantity_on_hand: int
    stock_quantity: int
    reference_number: str
    occurred_at: datetime
