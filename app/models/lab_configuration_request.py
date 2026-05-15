import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabConfigurationRequestStatus, LabConfigurationRequestType


class LabConfigurationRequest(Base):
    __tablename__ = "lab_configuration_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    request_type: Mapped[LabConfigurationRequestType] = mapped_column(
        Enum(LabConfigurationRequestType, name="lab_configuration_request_type"),
        nullable=False,
    )
    status: Mapped[LabConfigurationRequestStatus] = mapped_column(
        Enum(LabConfigurationRequestStatus, name="lab_configuration_request_status"),
        nullable=False,
        default=LabConfigurationRequestStatus.PENDING,
        server_default=LabConfigurationRequestStatus.PENDING.value,
    )
    department_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="Medical Laboratory",
        server_default="Medical Laboratory",
    )
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    linked_staff_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    linked_unit_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    linked_test_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "id",
            "clinic_id",
            name="uq_lab_configuration_requests_id_clinic",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_configuration_requests_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_lab_configuration_requests_requested_by",
        ),
        ForeignKeyConstraint(
            ["linked_staff_id"],
            ["users.id"],
            name="fk_lab_configuration_requests_linked_staff",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["linked_unit_id"],
            ["service_lines.id"],
            name="fk_lab_configuration_requests_linked_unit",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_lab_configuration_requests_resolved_by",
            ondelete="SET NULL",
        ),
    )
