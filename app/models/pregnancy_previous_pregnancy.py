# app/models/pregnancy_previous_pregnancy.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PregnancyPreviousPregnancy(Base):
    __tablename__ = "pregnancy_previous_pregnancies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    episode_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    year: Mapped[int | None] = mapped_column(nullable=True)
    duration: Mapped[str | None] = mapped_column(Text, nullable=True)
    antenatal_complications: Mapped[str | None] = mapped_column(Text, nullable=True)
    labour: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_alive: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_dead: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause_of_death: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_prev_pregnancies_id_clinic"),
        ForeignKeyConstraint(
            ["episode_id", "clinic_id"],
            ["pregnancy_episodes.id", "pregnancy_episodes.clinic_id"],
            name="fk_prev_pregnancies_episode_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_prev_pregnancies_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_prev_pregnancies_created_by",
        ),
    )
