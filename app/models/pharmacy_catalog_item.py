import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import (
    PharmacyCatalogLifecycleStatus,
    PharmacyInventoryClassification,
    PharmacyInventoryTrackingMode,
    PharmacyPricingStatus,
)


class PharmacyCatalogItem(Base):
    __tablename__ = "pharmacy_catalog_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    catalog_code: Mapped[str] = mapped_column(String(64), nullable=False)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dosage_form: Mapped[str] = mapped_column(String(80), nullable=False)
    dispense_unit: Mapped[str] = mapped_column(String(40), nullable=False)
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
    lifecycle_status: Mapped[PharmacyCatalogLifecycleStatus] = mapped_column(
        String(32),
        nullable=False,
        default=PharmacyCatalogLifecycleStatus.DRAFT.value,
        server_default=PharmacyCatalogLifecycleStatus.DRAFT.value,
    )
    billing_status: Mapped[PharmacyPricingStatus] = mapped_column(
        String(24),
        nullable=False,
        default=PharmacyPricingStatus.NOT_CONFIGURED.value,
        server_default=PharmacyPricingStatus.NOT_CONFIGURED.value,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cmd_reviewed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    cmd_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cmd_review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    priced_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    priced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", "catalog_code", name="uq_pharmacy_catalog_items_clinic_code"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_catalog_items_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_pharmacy_catalog_items_requested_by",
        ),
        ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
            name="fk_pharmacy_catalog_items_submitted_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["cmd_reviewed_by"],
            ["users.id"],
            name="fk_pharmacy_catalog_items_cmd_reviewed_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["priced_by"],
            ["users.id"],
            name="fk_pharmacy_catalog_items_priced_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["activated_by"],
            ["users.id"],
            name="fk_pharmacy_catalog_items_activated_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["deactivated_by"],
            ["users.id"],
            name="fk_pharmacy_catalog_items_deactivated_by",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "classification IN ('DRUG','CONSUMABLE','EQUIPMENT')",
            name="ck_pharmacy_catalog_items_classification",
        ),
        CheckConstraint(
            "tracking_mode IN ('LOT_TRACKED','QUANTITY_ONLY','SERIALIZED')",
            name="ck_pharmacy_catalog_items_tracking_mode",
        ),
        CheckConstraint(
            "lifecycle_status IN ('DRAFT','SUBMITTED','AWAITING_CMD_APPROVAL','CMD_APPROVED','PRICING_PENDING','PRICED','ACTIVE','REJECTED','DEACTIVATED')",
            name="ck_pharmacy_catalog_items_lifecycle_status",
        ),
        CheckConstraint(
            "billing_status IN ('NOT_CONFIGURED','PRICED','ACTIVE','INACTIVE')",
            name="ck_pharmacy_catalog_items_billing_status",
        ),
        Index("ix_pharmacy_catalog_items_clinic_status", "clinic_id", "lifecycle_status"),
        Index("ix_pharmacy_catalog_items_clinic_active", "clinic_id", "active"),
        Index("ix_pharmacy_catalog_items_clinic_name", "clinic_id", "generic_name"),
    )
