# app/models/lab_result.py
from sqlalchemy import String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.shared.enums import LabResultLifecycleStatus, RecordStatus
from datetime import datetime, timezone
import uuid


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    lab_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_requests.id"),
        nullable=False,
        index=True,
    )
    request_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lab_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )

    technician_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lab_result_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_version: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[LabResultLifecycleStatus] = mapped_column(
        Enum(LabResultLifecycleStatus, name="lab_result_lifecycle_status"),
        nullable=False,
        default=LabResultLifecycleStatus.RELEASED,
        server_default=LabResultLifecycleStatus.RELEASED.value,
    )
    entered_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    released_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    amended_from_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lab_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    amendment_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    result_value: Mapped[str] = mapped_column(String(255), nullable=False)
    result_unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    record_status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"),
        nullable=False,
        default=RecordStatus.DRAFT,
    )

    void_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
