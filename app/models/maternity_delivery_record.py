# app/models/maternity_delivery_record.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import BabySex, DeliveryMode, DeliveryOutcome, RecordStatus


class MaternityDeliveryRecord(Base):
    __tablename__ = "maternity_delivery_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"),
        nullable=False,
        default=RecordStatus.DRAFT,
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mode_of_delivery: Mapped[DeliveryMode] = mapped_column(
        Enum(DeliveryMode, name="delivery_mode"),
        nullable=False,
        default=DeliveryMode.UNKNOWN,
    )
    outcome: Mapped[DeliveryOutcome] = mapped_column(
        Enum(DeliveryOutcome, name="delivery_outcome"),
        nullable=False,
        default=DeliveryOutcome.UNKNOWN,
    )
    baby_sex: Mapped[BabySex] = mapped_column(
        Enum(BabySex, name="baby_sex"),
        nullable=False,
        default=BabySex.UNKNOWN,
    )
    baby_weight_kg: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    apgar_1: Mapped[int | None] = mapped_column(nullable=True)
    apgar_5: Mapped[int | None] = mapped_column(nullable=True)
    maternal_complications: Mapped[str | None] = mapped_column(Text, nullable=True)
    newborn_complications: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_maternity_delivery_id_clinic"),
        UniqueConstraint("clinic_id", "visit_id", name="uq_maternity_delivery_visit_clinic"),
        ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_maternity_delivery_visit_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["episode_id", "clinic_id"],
            ["pregnancy_episodes.id", "pregnancy_episodes.clinic_id"],
            name="fk_maternity_delivery_episode_clinic",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_maternity_delivery_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            name="fk_maternity_delivery_recorded_by",
        ),
    )
