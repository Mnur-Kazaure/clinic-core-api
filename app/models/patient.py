# models/patient.py
import uuid
from sqlalchemy import String, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.shared.enums import Gender
from datetime import date
import uuid



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
