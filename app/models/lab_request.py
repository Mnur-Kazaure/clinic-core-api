# app/models/lab_request.py
from sqlalchemy import String, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid

from app.models.base import Base
from app.shared.enums import LabRequestStatus, LabRequestWorkflowStatus


class LabRequest(Base):
    __tablename__ = "lab_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id"),
        nullable=False,
        index=True,
    )

    billing_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("billing_items.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
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
    test_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    lab_test_catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lab_test_catalog.id", ondelete="SET NULL"),
        nullable=True,
    )
    lab_test_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lab_test_config.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_lines.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_status: Mapped[LabRequestWorkflowStatus] = mapped_column(
        Enum(LabRequestWorkflowStatus, name="lab_request_workflow_status"),
        nullable=False,
        default=LabRequestWorkflowStatus.ORDERED,
        server_default=LabRequestWorkflowStatus.ORDERED.value,
    )

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
