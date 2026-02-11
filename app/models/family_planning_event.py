# app/models/family_planning_event.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import FamilyPlanningCommodity


class FamilyPlanningEvent(Base):
    __tablename__ = "family_planning_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    commodity: Mapped[FamilyPlanningCommodity] = mapped_column(
        Enum(FamilyPlanningCommodity, name="fp_commodity"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_fp_events_id_clinic"),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_fp_events_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_fp_events_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_fp_events_added_by",
        ),
    )
