import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PharmacyPricingStatus


class PharmacyPricingConfig(Base):
    __tablename__ = "pharmacy_pricing_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    charge_code: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="NGN",
        server_default="NGN",
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PharmacyPricingStatus] = mapped_column(
        String(24),
        nullable=False,
        default=PharmacyPricingStatus.PRICED.value,
        server_default=PharmacyPricingStatus.PRICED.value,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    configured_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    configured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "catalog_item_id",
            name="uq_pharmacy_pricing_configs_clinic_catalog_item",
        ),
        UniqueConstraint(
            "clinic_id",
            "charge_code",
            name="uq_pharmacy_pricing_configs_clinic_charge_code",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_pricing_configs_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["catalog_item_id"],
            ["pharmacy_catalog_items.id"],
            name="fk_pharmacy_pricing_configs_catalog_item",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["configured_by"],
            ["users.id"],
            name="fk_pharmacy_pricing_configs_configured_by",
        ),
        ForeignKeyConstraint(
            ["activated_by"],
            ["users.id"],
            name="fk_pharmacy_pricing_configs_activated_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["deactivated_by"],
            ["users.id"],
            name="fk_pharmacy_pricing_configs_deactivated_by",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "unit_price_minor >= 0",
            name="ck_pharmacy_pricing_configs_unit_price_non_negative",
        ),
        CheckConstraint(
            "status IN ('NOT_CONFIGURED','PRICED','ACTIVE','INACTIVE')",
            name="ck_pharmacy_pricing_configs_status",
        ),
        Index("ix_pharmacy_pricing_configs_clinic_status", "clinic_id", "status"),
        Index("ix_pharmacy_pricing_configs_clinic_active", "clinic_id", "active"),
    )
