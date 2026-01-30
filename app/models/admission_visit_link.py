# app/models/admission_visit_link.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AdmissionVisitLink(Base):
    __tablename__ = "admission_visit_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    admission_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("visit_id", "clinic_id", name="uq_admission_visit_links_visit_clinic"),
        ForeignKeyConstraint(
            ["admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_admission_visit_links_admission_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_admission_visit_links_visit_clinic",
            ondelete="CASCADE",
        ),
    )
