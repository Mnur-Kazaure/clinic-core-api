import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import BillingItemStatus


class BillingItem(Base):
    __tablename__ = "billing_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    visit_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    cashier_pay_point_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    charge_catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    pharmacy_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    pharmacy_pricing_config_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    charge_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    item_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    service_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OTHER",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    unit_price_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    total_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    amount_paid_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    status: Mapped[BillingItemStatus] = mapped_column(
        Enum(BillingItemStatus, name="billing_item_status"),
        nullable=False,
        default=BillingItemStatus.PENDING,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    payment_reference: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_billing_items_id_clinic"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_billing_items_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_billing_items_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_billing_items_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["cashier_pay_point_id"],
            ["cashier_pay_points.id"],
            name="fk_billing_items_cashier_pay_point",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["charge_catalog_id"],
            ["charge_catalog.id"],
            name="fk_billing_items_charge_catalog",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["pharmacy_catalog_item_id"],
            ["pharmacy_catalog_items.id"],
            name="fk_billing_items_pharmacy_catalog_item",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["pharmacy_pricing_config_id"],
            ["pharmacy_pricing_configs.id"],
            name="fk_billing_items_pharmacy_pricing_config",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_billing_items_created_by",
        ),
        CheckConstraint("quantity > 0", name="ck_billing_items_quantity_positive"),
        CheckConstraint(
            "unit_price_minor >= 0",
            name="ck_billing_items_unit_price_non_negative",
        ),
        CheckConstraint(
            "total_minor = quantity * unit_price_minor",
            name="ck_billing_items_total_matches",
        ),
        CheckConstraint(
            "amount_paid_minor >= 0 AND amount_paid_minor <= total_minor",
            name="ck_billing_items_amount_paid_range",
        ),
    )
