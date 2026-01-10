# app/models/lab_result.py
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from datetime import datetime
import uuid


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    lab_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_requests.id"),
        nullable=False,
        index=True,
    )

    technician_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    result_value: Mapped[str] = mapped_column(String(255), nullable=False)
    result_unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )