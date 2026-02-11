# app/models/visit.py

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import VisitStatus, VisitServiceLine


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"),
        nullable=False,
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
    )


    assigned_doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus, name="visit_status"),
        nullable=False,
    )

    service_line: Mapped[VisitServiceLine] = mapped_column(
        Enum(VisitServiceLine, name="visit_service_line"),
        nullable=False,
        default=VisitServiceLine.OPD,
        server_default=VisitServiceLine.OPD.value,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Optimistic concurrency token for state transitions.
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_visits_id_clinic"),
    )
