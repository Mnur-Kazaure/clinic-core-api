import uuid

from sqlalchemy import Boolean, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PharmacyUserUnitAccess(Base):
    __tablename__ = "pharmacy_user_unit_accesses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    service_line_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_user_unit_accesses_id_clinic"),
        UniqueConstraint(
            "user_id",
            "service_line_id",
            name="uq_pharmacy_user_unit_accesses_user_service_line",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_user_unit_accesses_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_pharmacy_user_unit_accesses_user",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_user_unit_accesses_service_line",
            ondelete="CASCADE",
        ),
    )
