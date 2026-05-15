import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReceiptSequence(Base):
    __tablename__ = "receipt_sequences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    prefix: Mapped[str] = mapped_column(String(20), nullable=False, default="RCPT")

    padding: Mapped[int] = mapped_column(Integer, nullable=False, default=6)

    last_number: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    reset_yearly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    current_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", name="uq_receipt_sequences_clinic"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_receipt_sequences_clinic",
            ondelete="CASCADE",
        ),
    )
