import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabStaffAssignmentStatus


class LabStaffAssignmentProfile(Base):
    __tablename__ = "lab_staff_assignment_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    assignment_status: Mapped[LabStaffAssignmentStatus] = mapped_column(
        Enum(LabStaffAssignmentStatus, name="lab_staff_assignment_status"),
        nullable=False,
        default=LabStaffAssignmentStatus.ACTIVE,
        server_default=LabStaffAssignmentStatus.ACTIVE.value,
    )
    coverage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
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
            "clinic_id",
            "user_id",
            name="uq_lab_staff_assignment_profiles_clinic_user",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_staff_assignment_profiles_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_lab_staff_assignment_profiles_user",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_lab_staff_assignment_profiles_updated_by",
        ),
    )
