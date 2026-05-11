# app/schemas/pharmacy.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, UUID4, ConfigDict, Field

from app.shared.enums import PrescriptionFulfillmentType
from app.shared.enums import PharmacyPrescriptionWorkflowStatus


# -----------------------------
# Request
# -----------------------------

class DispenseCreate(BaseModel):
    pharmacist_id: UUID4
    quantity: int
    unit_id: UUID4 | None = None
    stock_lot_id: UUID4 | None = None


class ExternalFulfillCreate(BaseModel):
    note: str = Field(..., min_length=3)


class DispensingReassignmentCreate(BaseModel):
    target_unit_id: UUID4
    reason: str = Field(..., min_length=3, max_length=200)
    note: str | None = None


# -----------------------------
# Response
# -----------------------------

class DispenseResponse(BaseModel):
    id: UUID4
    prescription_id: UUID4
    pharmacist_id: UUID4
    quantity: int
    quantity_dispensed_total: int
    quantity_remaining: int
    workflow_status: PharmacyPrescriptionWorkflowStatus
    dispensed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrescriptionFulfillmentResponse(BaseModel):
    id: UUID4
    clinic_id: UUID4
    prescription_id: UUID4
    actor_id: UUID4
    fulfillment_type: PrescriptionFulfillmentType
    quantity: Optional[int]
    note: Optional[str]
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DispensingReassignmentResponse(BaseModel):
    prescription_id: UUID4
    previous_unit_id: UUID4 | None = None
    target_unit_id: UUID4
    workflow_status: str
    reason: str
    note: str | None = None
