from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, UUID4

from app.shared.enums import (
    PharmacyIssueVoucherStatus,
    PharmacyReturnReasonCode,
    PharmacyReturnRequestStatus,
    PharmacyRefillRequestStatus,
    PharmacyRequestType,
)


class PharmacyRefillRequestItemCreateRequest(BaseModel):
    inventory_item_id: UUID4
    requested_quantity: int = Field(..., gt=0)
    note: str | None = None


class PharmacyRefillRequestCreateRequest(BaseModel):
    unit_id: UUID4 | None = None
    request_type: PharmacyRequestType = PharmacyRequestType.PHARMACY_REFILL
    urgency: str | None = Field(default=None, max_length=40)
    note: str | None = None
    items: list[PharmacyRefillRequestItemCreateRequest] = Field(min_length=1)


class PharmacyRefillRequestItemReviewRequest(BaseModel):
    refill_request_item_id: UUID4
    approved_quantity: int = Field(..., ge=0)


class PharmacyRefillRequestReviewRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    review_note: str | None = None
    items: list[PharmacyRefillRequestItemReviewRequest] | None = None


class PharmacyIssueVoucherItemCreateRequest(BaseModel):
    refill_request_item_id: UUID4
    batch_number: str = Field(..., min_length=1, max_length=80)
    expiry_date: date | None = None
    issued_quantity: int = Field(..., gt=0)


class PharmacyIssueVoucherCreateRequest(BaseModel):
    refill_request_id: UUID4
    store_unit_id: UUID4
    note: str | None = None
    items: list[PharmacyIssueVoucherItemCreateRequest] = Field(min_length=1)


class PharmacyIssueVoucherDispatchRequest(BaseModel):
    note: str | None = None


class PharmacyIssueVoucherItemAcknowledgeRequest(BaseModel):
    voucher_item_id: UUID4
    received_quantity: int = Field(..., ge=0)


class PharmacyIssueVoucherAcknowledgeRequest(BaseModel):
    unit_id: UUID4 | None = None
    note: str | None = None
    items: list[PharmacyIssueVoucherItemAcknowledgeRequest] = Field(min_length=1)


class PharmacyReturnRequestCreateRequest(BaseModel):
    unit_id: UUID4 | None = None
    issue_voucher_id: UUID4
    issue_voucher_item_id: UUID4
    quantity_now_returned: int = Field(..., gt=0)
    reason_code: PharmacyReturnReasonCode
    reason_note: str | None = None


class PharmacyReturnRequestReviewRequest(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    review_note: str | None = None


class PharmacyReturnRequestReceiveRequest(BaseModel):
    receive_note: str | None = None


class PharmacyRefillRequestItemResponse(BaseModel):
    id: UUID4
    inventory_item_id: UUID4
    inventory_item_name: str
    requested_quantity: int
    approved_quantity: int | None = None
    reserved_quantity: int = 0
    issued_quantity: int
    received_quantity: int
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PharmacyRefillRequestResponse(BaseModel):
    id: UUID4
    clinic_id: UUID4
    requesting_unit_id: UUID4
    requesting_unit_name: str
    requested_by: UUID4
    requested_by_name: str | None = None
    request_type: PharmacyRequestType
    status: PharmacyRefillRequestStatus
    urgency: str | None = None
    note: str | None = None
    reviewed_by: UUID4 | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    hod_visible_at: datetime | None = None
    requested_at: datetime
    requester_timeline: list[str] = Field(default_factory=list)
    items: list[PharmacyRefillRequestItemResponse]

    model_config = ConfigDict(from_attributes=True)


class PharmacyIssueVoucherItemResponse(BaseModel):
    id: UUID4
    inventory_item_id: UUID4
    inventory_item_name: str
    refill_request_item_id: UUID4 | None = None
    batch_number: str
    expiry_date: date | None = None
    issued_quantity: int
    received_quantity: int

    model_config = ConfigDict(from_attributes=True)


class PharmacyIssueVoucherResponse(BaseModel):
    id: UUID4
    clinic_id: UUID4
    voucher_number: str
    store_unit_id: UUID4
    store_unit_name: str
    receiving_unit_id: UUID4
    receiving_unit_name: str
    refill_request_id: UUID4 | None = None
    status: PharmacyIssueVoucherStatus
    prepared_by: UUID4 | None = None
    prepared_by_name: str | None = None
    prepared_at: datetime | None = None
    approved_by: UUID4 | None = None
    approved_by_name: str | None = None
    issued_by: UUID4 | None = None
    issued_by_name: str | None = None
    issued_at: datetime | None = None
    dispatched_by: UUID4 | None = None
    dispatched_at: datetime | None = None
    acknowledged_by: UUID4 | None = None
    acknowledged_by_name: str | None = None
    acknowledged_at: datetime | None = None
    closed_at: datetime | None = None
    note: str | None = None
    items: list[PharmacyIssueVoucherItemResponse]

    model_config = ConfigDict(from_attributes=True)


class PharmacyReturnRequestResponse(BaseModel):
    id: UUID4
    return_number: str
    clinic_id: UUID4
    issue_voucher_id: UUID4
    issue_voucher_number: str
    issue_voucher_item_id: UUID4
    refill_request_id: UUID4 | None = None
    returning_unit_id: UUID4
    returning_unit_name: str
    store_unit_id: UUID4
    store_unit_name: str
    inventory_item_id: UUID4
    inventory_item_name: str
    batch_number: str
    expiry_date: date | None = None
    original_issued_quantity: int
    quantity_already_returned: int
    quantity_now_returned: int
    quantity_received: int
    remaining_issued_balance: int
    eligible_return_quantity: int
    reason_code: PharmacyReturnReasonCode
    reason_note: str | None = None
    status: PharmacyReturnRequestStatus
    requested_by: UUID4
    requested_by_name: str | None = None
    requested_at: datetime
    reviewed_by: UUID4 | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    received_by: UUID4 | None = None
    received_by_name: str | None = None
    received_at: datetime | None = None
    receive_note: str | None = None
    closed_at: datetime | None = None
    return_timeline: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
