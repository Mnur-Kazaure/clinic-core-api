# app/models/bed.py
import uuid

from sqlalchemy import Enum, ForeignKeyConstraint, String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import BedStatus


class Bed(Base):
    __tablename__ = "beds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    ward_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    bed_label: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[BedStatus] = mapped_column(
        Enum(BedStatus, name="bed_status"),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_beds_id_clinic"),
        UniqueConstraint(
            "clinic_id",
            "ward_id",
            "bed_label",
            name="uq_beds_clinic_ward_label",
        ),
        ForeignKeyConstraint(
            ["ward_id", "clinic_id"],
            ["wards.id", "wards.clinic_id"],
            name="fk_beds_ward_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_beds_clinic_id",
            ondelete="CASCADE",
        ),
    )
