import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PaymentReceiptItem(Base):
    __tablename__ = "payment_receipt_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    billing_item_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    amount_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_payment_receipt_items_id_clinic"),
        UniqueConstraint(
            "receipt_id",
            "billing_item_id",
            name="uq_payment_receipt_items_receipt_billing_item",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_payment_receipt_items_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["receipt_id", "clinic_id"],
            ["payment_receipts.id", "payment_receipts.clinic_id"],
            name="fk_payment_receipt_items_receipt",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["billing_item_id", "clinic_id"],
            ["billing_items.id", "billing_items.clinic_id"],
            name="fk_payment_receipt_items_billing_item",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "amount_minor > 0",
            name="ck_payment_receipt_items_amount_positive",
        ),
    )
