# app/schemas/billing.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import BillingEntryType, BillingReasonCode


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
