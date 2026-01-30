# app/models/lab_request.py
from sqlalchemy import String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid

from app.models.base import Base
from app.shared.enums import LabRequestStatus


class LabRequest(Base):
    __tablename__ = "lab_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id"),
        nullable=False,
        index=True,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )

    requested_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    test_name: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[LabRequestStatus] = mapped_column(
        Enum(LabRequestStatus, name="lab_request_status"),
        nullable=False,
        default=LabRequestStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
