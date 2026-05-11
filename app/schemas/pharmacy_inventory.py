from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PharmacyInventoryCreateRequest(BaseModel):
    generic_name: str = Field(min_length=2, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    dosage_form: str = Field(min_length=2, max_length=80)
    strength: str | None = Field(default=None, max_length=80)
    unit_of_measure: str = Field(min_length=1, max_length=40)
    selling_price_minor: int = Field(ge=0)
    currency: str = Field(default="NGN", min_length=3, max_length=3)
    initial_stock: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    lifecycle_status: str = Field(default="ACTIVE", pattern="^(ACTIVE|INACTIVE)$")


class PharmacyInventoryUpdateRequest(BaseModel):
    generic_name: str | None = Field(default=None, min_length=2, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    dosage_form: str | None = Field(default=None, min_length=2, max_length=80)
    strength: str | None = Field(default=None, max_length=80)
    unit_of_measure: str | None = Field(default=None, min_length=1, max_length=40)
    selling_price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    lifecycle_status: str | None = Field(
        default=None,
        pattern="^(ACTIVE|INACTIVE)$",
    )
    note: str | None = Field(default=None, max_length=500)


class PharmacyRestockRequest(BaseModel):
    quantity: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class PharmacyAccessModeUpdateRequest(BaseModel):
    inventory_mode: str = Field(pattern="^(EDITABLE|READ_ONLY)$")


class PharmacyInventoryItemResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    generic_name: str
    brand_name: str | None
    dosage_form: str
    strength: str | None
    unit_of_measure: str
    selling_price_minor: int
    currency: str
    stock_quantity: int
    low_stock_threshold: int
    lifecycle_status: str
    last_restocked_at: datetime | None
    created_by: UUID
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PharmacyInventoryListResponse(BaseModel):
    data: list[PharmacyInventoryItemResponse]
    total: int
    page: int
    limit: int


class PharmacyStockMovementResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    inventory_item_id: UUID
    actor_id: UUID
    actor_name: str | None = None
    movement_type: str
    quantity_delta: int
    stock_before: int
    stock_after: int
    note: str | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    occurred_at: datetime


class PharmacyStockMovementListResponse(BaseModel):
    data: list[PharmacyStockMovementResponse]
    total: int
    limit: int
    offset: int


class PharmacyAccessModeResponse(BaseModel):
    inventory_mode: str
    changed_by: UUID | None = None
    changed_by_name: str | None = None
    changed_at: datetime | None = None


class PharmacyTopDispensedDrugResponse(BaseModel):
    drug_name: str
    dispensed_count: int


class PharmacyInventoryHealthResponse(BaseModel):
    available: int
    low_stock: int
    out_of_stock: int
    inactive: int


class PharmacyInventoryOverviewResponse(BaseModel):
    total_drugs: int
    low_stock: int
    out_of_stock: int
    todays_dispenses: int
    inventory_value_minor: int
    currency: str
    alerts: list[str]
    inventory_health: PharmacyInventoryHealthResponse
    recent_movements: list[PharmacyStockMovementResponse]
    top_dispensed_drugs: list[PharmacyTopDispensedDrugResponse]
    access_mode: PharmacyAccessModeResponse


class PharmacyReportsSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_movements: int
    restock_units: int
    dispensed_units: int
    price_updates: int
    lifecycle_changes: int
    low_stock_items: int
    out_of_stock_items: int
    inventory_value_minor: int
    currency: str
    recent_movements: list[PharmacyStockMovementResponse]


class PharmacyReportMovementRowResponse(BaseModel):
    id: UUID
    occurred_at: datetime
    movement_type: str
    quantity_delta: int
    stock_before: int
    stock_after: int
    note: str | None = None
    actor_name: str | None = None
    item_name: str


class PharmacyReportMovementListResponse(BaseModel):
    data: list[PharmacyReportMovementRowResponse]
    total: int
    page: int
    limit: int
    start_date: date
    end_date: date
