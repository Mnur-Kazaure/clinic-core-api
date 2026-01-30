# app/models/patient_alias.py
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKeyConstraint, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import (
    PatientAliasType,
    PatientAliasConfidence,
    PatientAliasSource,
)


class PatientAlias(Base):
    __tablename__ = "patient_aliases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    alias_type: Mapped[PatientAliasType] = mapped_column(
        Enum(PatientAliasType, name="patient_alias_type"),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[PatientAliasConfidence] = mapped_column(
        Enum(PatientAliasConfidence, name="patient_alias_confidence"),
        nullable=False,
    )
    source: Mapped[PatientAliasSource] = mapped_column(
        Enum(PatientAliasSource, name="patient_alias_source"),
        nullable=False,
    )
    captured_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_patient_alias_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_patient_alias_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["captured_by"],
            ["users.id"],
            name="fk_patient_alias_captured_by",
        ),
    )
