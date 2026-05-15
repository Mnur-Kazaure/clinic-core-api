import uuid

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PharmacyRefillRequestItem(Base):
    __tablename__ = "pharmacy_refill_request_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    refill_request_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    issued_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_refill_request_items_id_clinic"),
        UniqueConstraint(
            "refill_request_id",
            "inventory_item_id",
            name="uq_pharmacy_refill_request_items_request_item",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_refill_request_items_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["refill_request_id"],
            ["pharmacy_refill_requests.id"],
            name="fk_pharmacy_refill_request_items_request",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pharmacy_inventory_items.id"],
            name="fk_pharmacy_refill_request_items_inventory_item",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "requested_quantity > 0",
            name="ck_pharmacy_refill_request_items_requested_positive",
        ),
        CheckConstraint(
            "(approved_quantity IS NULL) OR (approved_quantity >= 0)",
            name="ck_pharmacy_refill_request_items_approved_non_negative",
        ),
        CheckConstraint(
            "reserved_quantity >= 0 AND issued_quantity >= 0 AND received_quantity >= 0",
            name="ck_pharmacy_refill_request_items_progress_non_negative",
        ),
    )
