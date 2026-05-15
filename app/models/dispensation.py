# models/dispensation.py
from datetime import date
import uuid

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class Dispensation(Base):
    __tablename__ = "dispensations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    pharmacist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    stock_lot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pharmacy_unit_stock_lots.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dispensing_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_lines.id", ondelete="SET NULL"),
        nullable=True,
    )
