# models/dispensation.py
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
import uuid

class Dispensation(Base):
    __tablename__ = "dispensations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    pharmacist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    quantity: Mapped[int] = mapped_column(Integer)