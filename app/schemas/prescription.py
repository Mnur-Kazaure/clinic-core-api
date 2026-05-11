# app/schemas/prescription.py
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, UUID4, Field, ConfigDict

from app.shared.enums import (
    PharmacyExceptionAuthorizationType,
    PharmacyPrescriptionWorkflowStatus,
    PrescriptionFulfillmentType,
    PrescriptionStatus,
    UserRole,
)


# -----------------------------
# Issue Prescription
# -----------------------------

class PrescriptionCreateRequest(BaseModel):
    consultation_id: UUID4

    pharmacy_catalog_item_id: UUID4 | None = None
    drug_name: str | None = Field(default=None, min_length=1)
    dosage: str = Field(..., min_length=1)
    frequency: str = Field(..., min_length=1)
    duration: str = Field(..., min_length=1)
    quantity_prescribed: Optional[int] = Field(default=None, ge=1)

    instructions: Optional[str] = None


# -----------------------------
# Dispense Prescription
# -----------------------------

class PrescriptionDispenseRequest(BaseModel):
    pharmacist_id: UUID4
    quantity: Optional[int] = None  # intentionally unused (Phase 11)


# -----------------------------
# Cancel Prescription
# -----------------------------

class PrescriptionCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3)


# -----------------------------
# Response
# -----------------------------


class PrescriptionStockLotOptionResponse(BaseModel):
    id: UUID4
    batch_number: str
    expiry_date: date | None = None
    quantity_on_hand: int
    low_stock: bool = False
    blocked: bool = False

    model_config = ConfigDict(from_attributes=True)


class PrescriptionReassignmentOptionResponse(BaseModel):
    unit_id: UUID4
    unit_name: str

class PrescriptionResponse(BaseModel):
    id: UUID4
    consultation_id: UUID4
    visit_id: UUID4
    patient_id: Optional[UUID4] = None
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None

    pharmacy_catalog_item_id: Optional[UUID4] = None
    drug_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str]
    quantity_prescribed: int
    quantity_dispensed_total: int
    quantity_remaining: int

    status: PrescriptionStatus
    workflow_status: PharmacyPrescriptionWorkflowStatus
    billing_item_id: Optional[UUID4] = None
    billing_status: Optional[str] = None
    assigned_dispensing_unit_id: Optional[UUID4] = None
    assigned_dispensing_unit_name: Optional[str] = None
    assigned_cashier_pay_point_id: Optional[UUID4] = None
    assigned_cashier_pay_point_name: Optional[str] = None
    exception_authorization_type: PharmacyExceptionAuthorizationType = (
        PharmacyExceptionAuthorizationType.NONE
    )
    payment_cleared: Optional[bool] = None
    source_department_name: Optional[str] = None
    priority: Optional[str] = None
    aging_minutes: Optional[int] = None
    local_stock_status: Optional[str] = None
    local_stock_available_quantity: int = 0
    local_stock_source: Optional[str] = None
    available_stock_lots: list[PrescriptionStockLotOptionResponse] = []
    reassignment_options: list[PrescriptionReassignmentOptionResponse] = []

    prescribed_by: UUID4
    prescribed_by_name: Optional[str] = None
    prescribed_by_role: Optional[UserRole] = None
    dispensed_by: Optional[UUID4]
    dispensed_by_name: Optional[str] = None
    dispensed_by_role: Optional[UserRole] = None

    issued_at: datetime
    dispensed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    externally_fulfilled_at: Optional[datetime] = None

    fulfillment_type: Optional[PrescriptionFulfillmentType] = None
    fulfillment_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
