# app/models/patient_mrn.py
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import MRNStatus


class PatientMRN(Base):
    __tablename__ = "patient_mrns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    mrn: Mapped[str] = mapped_column(
        sa.String().with_variant(postgresql.CITEXT(), "postgresql"),
        nullable=False,
    )
    status: Mapped[MRNStatus] = mapped_column(
        Enum(MRNStatus, name="mrn_status"),
        nullable=False,
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    check_digit: Mapped[str] = mapped_column(String(1), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retire_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", "mrn", name="uq_patient_mrns_clinic_mrn"),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_patient_mrns_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_patient_mrns_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["issued_by"],
            ["users.id"],
            name="fk_patient_mrns_issued_by",
        ),
    )
