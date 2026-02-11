# app/schemas/pharmacy.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, UUID4, ConfigDict, Field

from app.shared.enums import PrescriptionFulfillmentType


# -----------------------------
# Request
# -----------------------------

class DispenseCreate(BaseModel):
    pharmacist_id: UUID4
    quantity: int


class ExternalFulfillCreate(BaseModel):
    note: str = Field(..., min_length=3)


# -----------------------------
# Response
# -----------------------------

class DispenseResponse(BaseModel):
    id: UUID4
    prescription_id: UUID4
    pharmacist_id: UUID4
    quantity: int

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
