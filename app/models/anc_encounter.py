# app/models/anc_encounter.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import RecordStatus


class ANCEncounter(Base):
    __tablename__ = "anc_encounters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    episode_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"),
        nullable=False,
        default=RecordStatus.DRAFT,
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fundus_height: Mapped[str | None] = mapped_column(Text, nullable=True)
    presentation_position: Mapped[str | None] = mapped_column(Text, nullable=True)
    presenting_part: Mapped[str | None] = mapped_column(Text, nullable=True)
    foetal_heart: Mapped[str | None] = mapped_column(Text, nullable=True)
    bp_systolic: Mapped[int | None] = mapped_column(nullable=True)
    bp_diastolic: Mapped[int | None] = mapped_column(nullable=True)
    urine: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_anc_encounters_id_clinic"),
        UniqueConstraint("clinic_id", "visit_id", name="uq_anc_encounters_visit_clinic"),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_anc_encounters_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["episode_id", "clinic_id"],
            ["pregnancy_episodes.id", "pregnancy_episodes.clinic_id"],
            name="fk_anc_encounters_episode_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_anc_encounters_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            name="fk_anc_encounters_recorded_by",
        ),
    )
