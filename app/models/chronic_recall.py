import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import RecallIntervalUnit


class ChronicRecall(Base):
    __tablename__ = "chronic_recalls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id_canonical: Mapped[uuid.UUID] = mapped_column(nullable=False)
    condition_profile_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    assigned_clinician_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    interval_value: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_unit: Mapped[RecallIntervalUnit] = mapped_column(
        Enum(RecallIntervalUnit, name="recall_interval_unit"),
        nullable=False,
    )
    next_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    generation_paused: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    last_generated_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deactivated_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_chronic_recalls_clinic_active_due", "clinic_id", "active", "next_due_at"),
        Index("ix_chronic_recalls_patient_active", "clinic_id", "patient_id_canonical", "active"),
        Index(
            "uq_chronic_recalls_active_patient_condition",
            "clinic_id",
            "patient_id_canonical",
            "condition_profile_id",
            unique=True,
            postgresql_where=text("active = true"),
            sqlite_where=text("active = 1"),
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_chronic_recalls_clinic_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["patient_id_canonical", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_chronic_recalls_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["condition_profile_id", "clinic_id"],
            ["condition_profiles.id", "condition_profiles.clinic_id"],
            name="fk_chronic_recalls_condition_profile_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["assigned_clinician_id"],
            ["users.id"],
            name="fk_chronic_recalls_assigned_clinician",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_chronic_recalls_created_by",
        ),
    )
