# app/models/clinic_mrn_sequence.py
import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ClinicMrnSequence(Base):
    __tablename__ = "clinic_mrn_sequences"

    clinic_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    prefix: Mapped[str | None] = mapped_column(String(16), nullable=True)
    next_value: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("next_value >= 1", name="ck_clinic_mrn_sequences_next_value"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_clinic_mrn_sequences_clinic",
            ondelete="CASCADE",
        ),
    )
