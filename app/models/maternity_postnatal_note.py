# app/models/maternity_postnatal_note.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PostnatalSubject


class MaternityPostnatalNote(Base):
    __tablename__ = "maternity_postnatal_notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    subject: Mapped[PostnatalSubject] = mapped_column(
        Enum(PostnatalSubject, name="postnatal_subject"),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    added_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_postnatal_notes_id_clinic"),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_postnatal_notes_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_postnatal_notes_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_postnatal_notes_added_by",
        ),
    )
