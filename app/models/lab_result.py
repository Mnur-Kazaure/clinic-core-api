# models/lab_result.py
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
import uuid

class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lab_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lab_requests.id"))
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    result_value: Mapped[str] = mapped_column(String(255))
    result_unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100)
)