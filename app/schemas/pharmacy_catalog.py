from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import (
    PharmacyCatalogLifecycleStatus,
    PharmacyInventoryClassification,
    PharmacyInventoryTrackingMode,
    PharmacyPricingStatus,
)


class PharmacyCatalogRequestCreateRequest(BaseModel):
    generic_name: str = Field(min_length=2, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    strength: str | None = Field(default=None, max_length=80)
    dosage_form: str = Field(min_length=2, max_length=80)
    dispense_unit: str = Field(min_length=1, max_length=40)
    classification: PharmacyInventoryClassification = PharmacyInventoryClassification.DRUG
    tracking_mode: PharmacyInventoryTrackingMode = PharmacyInventoryTrackingMode.LOT_TRACKED
    requires_expiry: bool = True
    justification: str = Field(min_length=5, max_length=2000)
    submit_now: bool = True


class PharmacyCatalogRequestSubmitRequest(BaseModel):
    submit: bool = True


class PharmacyCatalogRequestReviewRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    note: str | None = Field(default=None, max_length=1000)


class PharmacyPricingConfigUpsertRequest(BaseModel):
    charge_code: str = Field(min_length=3, max_length=64)
    unit_price_minor: int = Field(ge=0)
    currency: str = Field(default="NGN", min_length=3, max_length=3)
    effective_date: date
    activate: bool = True


class PharmacyCatalogRegistryRowResponse(BaseModel):
    id: UUID
    catalog_code: str
    generic_name: str
    brand_name: str | None = None
    strength: str | None = None
    dosage_form: str
    dispense_unit: str
    classification: PharmacyInventoryClassification
    tracking_mode: PharmacyInventoryTrackingMode
    requires_expiry: bool
    lifecycle_status: PharmacyCatalogLifecycleStatus
    billing_status: PharmacyPricingStatus
    active: bool
    justification: str
    requested_by: UUID
    requested_by_name: str | None = None
    submitted_by: UUID | None = None
    submitted_by_name: str | None = None
    submitted_at: datetime | None = None
    cmd_reviewed_by: UUID | None = None
    cmd_reviewed_by_name: str | None = None
    cmd_reviewed_at: datetime | None = None
    cmd_review_note: str | None = None
    priced_by: UUID | None = None
    priced_by_name: str | None = None
    priced_at: datetime | None = None
    activated_by: UUID | None = None
    activated_by_name: str | None = None
    activated_at: datetime | None = None
    deactivated_by: UUID | None = None
    deactivated_by_name: str | None = None
    deactivated_at: datetime | None = None
    current_price_minor: int | None = None
    current_currency: str | None = None
    charge_code: str | None = None
    effective_date: date | None = None

    model_config = ConfigDict(from_attributes=True)


class PharmacyPricingConfigResponse(BaseModel):
    id: UUID
    catalog_item_id: UUID
    charge_code: str
    unit_price_minor: int
    currency: str
    effective_date: date
    status: PharmacyPricingStatus
    active: bool
    configured_by: UUID
    configured_by_name: str | None = None
    configured_at: datetime | None = None
    activated_by: UUID | None = None
    activated_by_name: str | None = None
    activated_at: datetime | None = None
    deactivated_by: UUID | None = None
    deactivated_by_name: str | None = None
    deactivated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PharmacyCatalogGovernanceDetailResponse(BaseModel):
    item: PharmacyCatalogRegistryRowResponse
    pricing: PharmacyPricingConfigResponse | None = None


class PharmacyCatalogListResponse(BaseModel):
    data: list[PharmacyCatalogRegistryRowResponse]


class PharmacyActiveCatalogItemResponse(BaseModel):
    id: UUID
    catalog_code: str
    generic_name: str
    brand_name: str | None = None
    strength: str | None = None
    dosage_form: str
    dispense_unit: str
    classification: PharmacyInventoryClassification
    tracking_mode: PharmacyInventoryTrackingMode
    requires_expiry: bool
    charge_code: str
    unit_price_minor: int
    currency: str
    display_name: str


