# app/models/pregnancy_episode.py
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PregnancyEpisodeStatus


class PregnancyEpisode(Base):
    __tablename__ = "pregnancy_episodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[PregnancyEpisodeStatus] = mapped_column(
        Enum(PregnancyEpisodeStatus, name="pregnancy_episode_status"),
        nullable=False,
        default=PregnancyEpisodeStatus.ACTIVE,
    )
    lmp_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    edd_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gravida: Mapped[int | None] = mapped_column(nullable=True)
    parity: Mapped[int | None] = mapped_column(nullable=True)
    booking_reg_no: Mapped[str | None] = mapped_column(Text, nullable=True)
    past_medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    past_surgical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    history_present_pregnancy: Mapped[str | None] = mapped_column(Text, nullable=True)
    general_exam: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pregnancy_episodes_id_clinic"),
        ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_pregnancy_episodes_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pregnancy_episodes_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_pregnancy_episodes_created_by",
        ),
    )
