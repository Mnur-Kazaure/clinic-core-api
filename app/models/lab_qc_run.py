import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabQcStatus


class LabQcRun(Base):
    __tablename__ = "lab_qc_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    machine_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    qc_level: Mapped[str] = mapped_column(String(64), nullable=False)
    performed_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    status: Mapped[LabQcStatus] = mapped_column(
        Enum(LabQcStatus, name="lab_qc_status"),
        nullable=False,
        default=LabQcStatus.PASS,
        server_default=LabQcStatus.PASS.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_qc_runs_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["unit_id"],
            ["service_lines.id"],
            name="fk_lab_qc_runs_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["performed_by"],
            ["users.id"],
            name="fk_lab_qc_runs_performed_by",
        ),
    )
