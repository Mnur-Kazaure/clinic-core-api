import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Boolean,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PharmacyInventoryClassification, PharmacyInventoryTrackingMode


class PharmacyInventoryItem(Base):
    __tablename__ = "pharmacy_inventory_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    generic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dosage_form: Mapped[str] = mapped_column(String(80), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(80), nullable=True)
    unit_of_measure: Mapped[str] = mapped_column(String(40), nullable=False)
    classification: Mapped[PharmacyInventoryClassification] = mapped_column(
        String(24),
        nullable=False,
        default=PharmacyInventoryClassification.DRUG.value,
        server_default=PharmacyInventoryClassification.DRUG.value,
    )
    tracking_mode: Mapped[PharmacyInventoryTrackingMode] = mapped_column(
        String(24),
        nullable=False,
        default=PharmacyInventoryTrackingMode.LOT_TRACKED.value,
        server_default=PharmacyInventoryTrackingMode.LOT_TRACKED.value,
    )
    requires_expiry: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    selling_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")

    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    lifecycle_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="ACTIVE",
    )

    last_restocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "catalog_item_id",
            name="uq_pharmacy_inventory_catalog_item",
        ),
        UniqueConstraint(
            "clinic_id",
            "generic_name",
            "brand_name",
            "dosage_form",
            "strength",
            "unit_of_measure",
            name="uq_pharmacy_inventory_identity",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_inventory_items_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["catalog_item_id"],
            ["pharmacy_catalog_items.id"],
            name="fk_pharmacy_inventory_items_catalog_item",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_pharmacy_inventory_items_created_by",
        ),
        ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_pharmacy_inventory_items_updated_by",
        ),
        CheckConstraint(
            "selling_price_minor >= 0",
            name="ck_pharmacy_inventory_items_price_non_negative",
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_pharmacy_inventory_items_stock_non_negative",
        ),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_pharmacy_inventory_items_threshold_non_negative",
        ),
        CheckConstraint(
            "lifecycle_status IN ('ACTIVE','INACTIVE')",
            name="ck_pharmacy_inventory_items_lifecycle_status",
        ),
        CheckConstraint(
            "classification IN ('DRUG','CONSUMABLE','EQUIPMENT')",
            name="ck_pharmacy_inventory_items_classification",
        ),
        CheckConstraint(
            "tracking_mode IN ('LOT_TRACKED','QUANTITY_ONLY','SERIALIZED')",
            name="ck_pharmacy_inventory_items_tracking_mode",
        ),
        Index(
            "ix_pharmacy_inventory_items_clinic_name",
            "clinic_id",
            "generic_name",
        ),
        Index(
            "ix_pharmacy_inventory_items_catalog_item",
            "catalog_item_id",
        ),
        Index(
            "ix_pharmacy_inventory_items_clinic_status",
            "clinic_id",
            "lifecycle_status",
        ),
    )
