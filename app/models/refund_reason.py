import uuid

from sqlalchemy import Boolean, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RefundReason(Base):
    __tablename__ = "refund_reasons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason_code: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", "reason_code", name="uq_refund_reasons_clinic_code"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_refund_reasons_clinic",
            ondelete="CASCADE",
        ),
    )

