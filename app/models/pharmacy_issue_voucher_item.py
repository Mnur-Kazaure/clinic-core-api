import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PharmacyIssueVoucherItem(Base):
    __tablename__ = "pharmacy_issue_voucher_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    voucher_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    refill_request_item_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    batch_number: Mapped[str] = mapped_column(String(80), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    issued_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_issue_voucher_items_id_clinic"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_issue_voucher_items_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["voucher_id"],
            ["pharmacy_issue_vouchers.id"],
            name="fk_pharmacy_issue_voucher_items_voucher",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["refill_request_item_id"],
            ["pharmacy_refill_request_items.id"],
            name="fk_pharmacy_issue_voucher_items_request_item",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pharmacy_inventory_items.id"],
            name="fk_pharmacy_issue_voucher_items_inventory_item",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "issued_quantity > 0",
            name="ck_pharmacy_issue_voucher_items_issued_positive",
        ),
        CheckConstraint(
            "received_quantity >= 0 AND received_quantity <= issued_quantity",
            name="ck_pharmacy_issue_voucher_items_received_range",
        ),
    )
