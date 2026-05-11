import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabSpecimenEventType


class LabSpecimenEvent(Base):
    __tablename__ = "lab_specimen_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    specimen_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[LabSpecimenEventType] = mapped_column(
        Enum(LabSpecimenEventType, name="lab_specimen_event_type"),
        nullable=False,
    )
    performed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["specimen_id"],
            ["lab_specimens.id"],
            name="fk_lab_specimen_events_specimen",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["performed_by"],
            ["users.id"],
            name="fk_lab_specimen_events_performed_by",
        ),
    )
