# app/models/visit_status_history.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Enum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import VisitStatus


class VisitStatusHistory(Base):
    __tablename__ = "visit_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus),
        nullable=False,
    )

    to_status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus),
        nullable=False,
    )

    changed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
