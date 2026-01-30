# app/models/clinical_priority_event.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import ClinicalPriorityLevel, ClinicalPrioritySource


class ClinicalPriorityEvent(Base):
    __tablename__ = "clinical_priority_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    level: Mapped[ClinicalPriorityLevel] = mapped_column(
        Enum(ClinicalPriorityLevel, name="clinical_priority_level"),
        nullable=False,
    )
    source: Mapped[ClinicalPrioritySource] = mapped_column(
        Enum(ClinicalPrioritySource, name="clinical_priority_source"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    set_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_priority_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_priority_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_priority_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["set_by"],
            ["users.id"],
            name="fk_priority_set_by",
        ),
    )
