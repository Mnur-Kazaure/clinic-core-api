import uuid

from sqlalchemy import Boolean, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CashierPayPoint(Base):
    __tablename__ = "cashier_pay_points"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_cashier_pay_points_id_clinic"),
        UniqueConstraint("clinic_id", "code", name="uq_cashier_pay_points_clinic_code"),
        UniqueConstraint("clinic_id", "name", name="uq_cashier_pay_points_clinic_name"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_cashier_pay_points_clinic",
            ondelete="CASCADE",
        ),
    )
