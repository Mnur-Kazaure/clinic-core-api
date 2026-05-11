import uuid

from sqlalchemy import Boolean, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CashierPayPointAccess(Base):
    __tablename__ = "cashier_pay_point_accesses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    cashier_pay_point_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_cashier_pay_point_accesses_id_clinic"),
        UniqueConstraint(
            "user_id",
            "cashier_pay_point_id",
            name="uq_cashier_pay_point_accesses_user_pay_point",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_cashier_pay_point_accesses_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_cashier_pay_point_accesses_user",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["cashier_pay_point_id"],
            ["cashier_pay_points.id"],
            name="fk_cashier_pay_point_accesses_pay_point",
            ondelete="CASCADE",
        ),
    )
