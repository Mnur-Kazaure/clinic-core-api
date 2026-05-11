# app/models/visit.py

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import (
    ClinicalPriorityLevel,
    VisitServiceLine,
    VisitStatus,
    VisitTriageState,
)


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


    assigned_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    linked_follow_up_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("follow_ups.id", ondelete="SET NULL"),
        nullable=True,
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

    # Table-driven service line hierarchy (Phase 1 expansion).
    service_line_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_lines.id"),
        nullable=True,
    )

    triage_state: Mapped[VisitTriageState] = mapped_column(
        Enum(VisitTriageState, name="visit_triage_state"),
        nullable=False,
        default=VisitTriageState.PENDING,
        server_default=VisitTriageState.PENDING.value,
    )

    triage_acuity: Mapped[ClinicalPriorityLevel | None] = mapped_column(
        Enum(ClinicalPriorityLevel, name="clinical_priority_level"),
        nullable=True,
    )

    triaged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    triaged_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
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
