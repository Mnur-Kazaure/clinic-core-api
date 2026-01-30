# app/models/patient_identity_map.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PatientIdentityMap(Base):
    __tablename__ = "patient_identity_map"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    from_patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    to_patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    mapped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    mapped_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("clinic_id", "from_patient_id", name="uq_identity_map_from_patient"),
        UniqueConstraint("id", "clinic_id", name="uq_identity_map_id_clinic"),
        ForeignKeyConstraint(
            ["from_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_map_from_patient",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["to_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_map_to_patient",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_map_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["mapped_by"],
            ["users.id"],
            name="fk_identity_map_mapped_by",
        ),
        CheckConstraint(
            "from_patient_id != to_patient_id",
            name="ck_identity_map_not_self",
        ),
    )
