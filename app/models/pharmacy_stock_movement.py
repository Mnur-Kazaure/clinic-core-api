import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PharmacyStockMovement(Base):
    __tablename__ = "pharmacy_stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    service_line_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    movement_type: Mapped[str] = mapped_column(String(24), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_before: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)

    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_stock_movements_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pharmacy_inventory_items.id"],
            name="fk_pharmacy_stock_movements_inventory_item",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_stock_movements_service_line",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_pharmacy_stock_movements_actor",
        ),
        CheckConstraint(
            "movement_type IN ('RESTOCK','DISPENSE','ISSUE','RECEIVE','RETURN','ADJUSTMENT','PRICE_UPDATE','ACTIVATED','INACTIVATED')",
            name="ck_pharmacy_stock_movements_type",
        ),
        CheckConstraint(
            "stock_before >= 0 AND stock_after >= 0",
            name="ck_pharmacy_stock_movements_stock_non_negative",
        ),
        CheckConstraint(
            "stock_after = stock_before + quantity_delta",
            name="ck_pharmacy_stock_movements_stock_transition",
        ),
        Index(
            "ix_pharmacy_stock_movements_clinic_occurred_at",
            "clinic_id",
            "occurred_at",
        ),
        Index(
            "ix_pharmacy_stock_movements_item_occurred_at",
            "inventory_item_id",
            "occurred_at",
        ),
    )
