from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, UUID4

from app.schemas.pharmacy_supply import (
    PharmacyIssueVoucherResponse,
    PharmacyRefillRequestResponse,
    PharmacyReturnRequestResponse,
)
from app.shared.enums import (
    PharmacyExceptionAuthorizationType,
    PharmacyPrescriptionWorkflowStatus,
)


class PharmacyDispensingOverviewResponse(BaseModel):
    assigned_prescriptions: int
    ready_to_dispense: int
    awaiting_payment_clearance: int
    reassigned: int
    out_of_stock: int
    completed_today: int
    last_updated_at: datetime


class PharmacyDispensingNextActionResponse(BaseModel):
    severity: Literal['info', 'warning', 'critical']
    title: str
    detail: str


class PharmacyDispensingReassignmentTargetResponse(BaseModel):
    unit_id: UUID4
    unit_name: str


class PharmacyDispensingQueueRowResponse(BaseModel):
    prescription_id: UUID4
    visit_id: UUID4
    patient_id: UUID4 | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    source_department_name: str | None = None
    item_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None = None
    quantity_prescribed: int
    quantity_dispensed_total: int
    quantity_remaining: int
    readiness_state: PharmacyPrescriptionWorkflowStatus
    payment_state: str
    assigned_unit_id: UUID4 | None = None
    assigned_unit_name: str | None = None
    cashier_pay_point_name: str | None = None
    priority: Literal['ROUTINE', 'URGENT', 'EMERGENCY']
    aging_minutes: int
    exception_authorization_type: PharmacyExceptionAuthorizationType
    local_stock_status: Literal['IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK', 'EXPIRED', 'UNMAPPED']
    local_stock_available_quantity: int
    prescribed_by_name: str | None = None
    dispensed_by_name: str | None = None
    issued_at: datetime
    dispensed_at: datetime | None = None
    recently_reassigned: bool = False
    last_reassignment_at: datetime | None = None
    reassignment_reason: str | None = None
    reassignment_note: str | None = None


class PharmacyDispensingLocalStockRowResponse(BaseModel):
    inventory_item_id: UUID4
    item_name: str
    batch_number: str
    expiry_date: date | None = None
    quantity_on_hand: int
    low_stock_threshold: int
    stock_status: Literal['IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK', 'EXPIRED']
    blocked: bool = False
    source_label: str = 'Local Unit Stock'


class PharmacyDispensingAlertRowResponse(BaseModel):
    id: str
    severity: Literal['info', 'warning', 'critical']
    alert_type: str
    title: str
    detail: str
    patient_id: UUID4 | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    item_name: str | None = None
    occurred_at: datetime


class PharmacyDispensingActivityRowResponse(BaseModel):
    id: str
    occurred_at: datetime
    action_type: str
    summary: str
    detail: str | None = None
    actor_name: str | None = None
    patient_id: UUID4 | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    item_name: str | None = None
    severity: Literal['info', 'warning', 'critical']


class PharmacyDispensingDashboardResponse(BaseModel):
    generated_at: datetime
    unit_id: UUID4
    unit_name: str
    overview: PharmacyDispensingOverviewResponse
    next_action: PharmacyDispensingNextActionResponse | None = None
    reassignment_targets: list[PharmacyDispensingReassignmentTargetResponse]
    prescriptions: list[PharmacyDispensingQueueRowResponse]
    local_stock: list[PharmacyDispensingLocalStockRowResponse]
    refill_requests: list[PharmacyRefillRequestResponse]
    issue_vouchers: list[PharmacyIssueVoucherResponse]
    return_requests: list[PharmacyReturnRequestResponse]
    alerts: list[PharmacyDispensingAlertRowResponse]
    activity_audit: list[PharmacyDispensingActivityRowResponse]


class PharmacyDispensingStockLotResponse(BaseModel):
    id: UUID4
    batch_number: str
    expiry_date: date | None = None
    quantity_on_hand: int
    low_stock: bool = False
    blocked: bool = False

    model_config = ConfigDict(from_attributes=True)


class PharmacyDispensingPrescriptionDetailResponse(BaseModel):
    id: UUID4
    available_stock_lots: list[PharmacyDispensingStockLotResponse] = []
    local_stock_available_quantity: int = 0
    local_stock_status: Literal['IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK', 'EXPIRED', 'UNMAPPED'] = 'UNMAPPED'
    local_stock_source: str = 'Local Unit Stock'
    reassignment_targets: list[PharmacyDispensingReassignmentTargetResponse] = []

    model_config = ConfigDict(from_attributes=True)
