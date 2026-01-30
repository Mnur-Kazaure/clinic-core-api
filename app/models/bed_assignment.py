# app/models/bed_assignment.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import BedAssignmentType


class BedAssignment(Base):
    __tablename__ = "bed_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    admission_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    bed_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    assigned_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    assignment_type: Mapped[BedAssignmentType] = mapped_column(
        Enum(BedAssignmentType, name="bed_assignment_type"),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_bed_assignments_admission_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["bed_id", "clinic_id"],
            ["beds.id", "beds.clinic_id"],
            name="fk_bed_assignments_bed_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
            name="fk_bed_assignments_assigned_by",
        ),
        CheckConstraint(
            "(assignment_type != 'TRANSFER') OR (reason IS NOT NULL AND length(reason) >= 3)",
            name="ck_bed_assignment_transfer_reason",
        ),
    )
