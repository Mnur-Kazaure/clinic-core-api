import uuid
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PharmacyUnitStockLot(Base):
    __tablename__ = "pharmacy_unit_stock_lots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    service_line_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    batch_number: Mapped[str] = mapped_column(String(80), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_unit_stock_lots_id_clinic"),
        UniqueConstraint(
            "service_line_id",
            "inventory_item_id",
            "batch_number",
            "expiry_date",
            name="uq_pharmacy_unit_stock_lots_unit_item_batch",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_unit_stock_lots_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_unit_stock_lots_service_line",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pharmacy_inventory_items.id"],
            name="fk_pharmacy_unit_stock_lots_inventory_item",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "quantity_on_hand >= 0",
            name="ck_pharmacy_unit_stock_lots_quantity_non_negative",
        ),
        Index(
            "ix_pharmacy_unit_stock_lots_unit_item",
            "service_line_id",
            "inventory_item_id",
        ),
    )
