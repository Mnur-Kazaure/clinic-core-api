# app/models/patient.py
import uuid
from sqlalchemy import String, Date, Enum, ForeignKey, UniqueConstraint, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.shared.enums import Gender, IdentityState
from datetime import date, datetime
import uuid


# app/models/patient.py
class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender))
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation: Mapped[str] = mapped_column(String(100), nullable=False)

    identity_state: Mapped[IdentityState] = mapped_column(
        Enum(IdentityState, name="identity_state"),
        nullable=False,
        default=IdentityState.VERIFIED,
    )
    created_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_patients_id_clinic"),
    )
