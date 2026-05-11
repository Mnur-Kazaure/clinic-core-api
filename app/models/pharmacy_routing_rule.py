import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import VisitServiceLine


class PharmacyRoutingRule(Base):
    __tablename__ = "pharmacy_routing_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    visit_service_line: Mapped[VisitServiceLine | None] = mapped_column(
        Enum(VisitServiceLine, name="visit_service_line"),
        nullable=True,
    )
    visit_service_line_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    scheme_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    min_age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispensing_unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    cashier_pay_point_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_routing_rules_id_clinic"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_routing_rules_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["visit_service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_routing_rules_visit_service_line",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["dispensing_unit_id"],
            ["service_lines.id"],
            name="fk_pharmacy_routing_rules_dispensing_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["cashier_pay_point_id"],
            ["cashier_pay_points.id"],
            name="fk_pharmacy_routing_rules_pay_point",
            ondelete="RESTRICT",
        ),
    )
