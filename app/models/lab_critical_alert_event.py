import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabCriticalAlertEventType


class LabCriticalAlertEvent(Base):
    __tablename__ = "lab_critical_alert_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[LabCriticalAlertEventType] = mapped_column(
        Enum(LabCriticalAlertEventType, name="lab_critical_alert_event_type"),
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
            ["alert_id"],
            ["lab_critical_alerts.id"],
            name="fk_lab_critical_alert_events_alert",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["performed_by"],
            ["users.id"],
            name="fk_lab_critical_alert_events_performed_by",
            ondelete="SET NULL",
        ),
    )
