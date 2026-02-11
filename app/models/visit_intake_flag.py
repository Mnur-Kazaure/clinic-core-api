# app/models/visit_intake_flag.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKeyConstraint, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VisitIntakeFlag(Base):
    __tablename__ = "visit_intake_flags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    set_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_visit_intake_flags_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_visit_intake_flags_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["set_by"],
            ["users.id"],
            name="fk_visit_intake_flags_set_by",
        ),
    )
