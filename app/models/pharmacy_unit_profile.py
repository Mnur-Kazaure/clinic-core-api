import uuid

from sqlalchemy import Enum, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PharmacyUnitCategory, VisitServiceLine


class PharmacyUnitProfile(Base):
    __tablename__ = "pharmacy_unit_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    service_line_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    unit_category: Mapped[PharmacyUnitCategory] = mapped_column(
        Enum(PharmacyUnitCategory, name="pharmacy_unit_category"),
        nullable=False,
    )
    scheme_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    linked_visit_service_line: Mapped[VisitServiceLine | None] = mapped_column(
        Enum(VisitServiceLine, name="visit_service_line"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_unit_profiles_id_clinic"),
        UniqueConstraint(
            "service_line_id",
            name="uq_pharmacy_unit_profiles_service_line",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_unit_profiles_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_unit_profiles_service_line",
            ondelete="CASCADE",
        ),
    )
