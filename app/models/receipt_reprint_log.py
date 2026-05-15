import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReceiptReprintLog(Base):
    __tablename__ = "receipt_reprint_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    receipt_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    reprinted_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reprinted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_receipt_reprint_logs_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["receipt_id", "clinic_id"],
            ["payment_receipts.id", "payment_receipts.clinic_id"],
            name="fk_receipt_reprint_logs_receipt",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["reprinted_by"],
            ["users.id"],
            name="fk_receipt_reprint_logs_reprinted_by",
        ),
    )
