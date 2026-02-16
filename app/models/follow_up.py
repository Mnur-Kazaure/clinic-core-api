import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import (
    FollowUpGeneratedBy,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
)


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    patient_id_canonical: Mapped[uuid.UUID] = mapped_column(nullable=False)
    type: Mapped[FollowUpType] = mapped_column(
        Enum(FollowUpType, name="follow_up_type"),
        nullable=False,
    )
    priority: Mapped[FollowUpPriority] = mapped_column(
        Enum(FollowUpPriority, name="follow_up_priority"),
        nullable=False,
    )
    status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, name="follow_up_status"),
        nullable=False,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    origin_visit_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    origin_admission_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    chronic_recall_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    completed_visit_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancel_reason_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_by: Mapped[FollowUpGeneratedBy] = mapped_column(
        Enum(FollowUpGeneratedBy, name="follow_up_generated_by"),
        nullable=False,
        default=FollowUpGeneratedBy.USER,
        server_default=FollowUpGeneratedBy.USER.value,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_follow_ups_id_clinic"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_follow_ups_clinic_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["patient_id_canonical", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_follow_ups_patient_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_follow_ups_owner_user_id",
        ),
        ForeignKeyConstraint(
            ["origin_visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_follow_ups_origin_visit_clinic",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["completed_visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_follow_ups_completed_visit_clinic",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["origin_admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_follow_ups_origin_admission_clinic",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["chronic_recall_id"],
            ["chronic_recalls.id"],
            name="fk_follow_ups_chronic_recall_id",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_follow_ups_created_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["rescheduled_from_id"],
            ["follow_ups.id"],
            name="fk_follow_ups_rescheduled_from_id",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "(status != 'COMPLETED') OR "
            "(completed_visit_id IS NOT NULL AND completed_at IS NOT NULL)",
            name="ck_follow_ups_completed_requires_visit_and_timestamp",
        ),
        Index(
            "uq_follow_ups_chronic_recall_scheduled",
            "clinic_id",
            "chronic_recall_id",
            unique=True,
            postgresql_where=text(
                "type = 'CHRONIC_RECALL' AND status = 'SCHEDULED' "
                "AND chronic_recall_id IS NOT NULL"
            ),
            sqlite_where=text(
                "type = 'CHRONIC_RECALL' AND status = 'SCHEDULED' "
                "AND chronic_recall_id IS NOT NULL"
            ),
        ),
        Index("ix_follow_ups_clinic_status_due_at", "clinic_id", "status", "due_at"),
        Index("ix_follow_ups_clinic_chronic_recall", "clinic_id", "chronic_recall_id"),
    )
