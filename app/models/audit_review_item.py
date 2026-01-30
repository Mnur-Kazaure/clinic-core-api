# app/models/audit_review_item.py
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKeyConstraint, Text, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import AuditItemType


class AuditReviewItem(Base):
    __tablename__ = "audit_review_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    item_type: Mapped[AuditItemType] = mapped_column(
        Enum(AuditItemType, name="audit_item_type"),
        nullable=False,
    )
    access_log_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    event_log_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    added_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(item_type = 'ACCESS_LOG' AND access_log_id IS NOT NULL AND event_log_id IS NULL) OR "
            "(item_type = 'EVENT_LOG' AND event_log_id IS NOT NULL AND access_log_id IS NULL)",
            name="ck_audit_review_item_type",
        ),
        ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["audit_review_cases.id", "audit_review_cases.clinic_id"],
            name="fk_audit_review_item_case",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["access_log_id", "clinic_id"],
            ["access_logs.id", "access_logs.clinic_id"],
            name="fk_audit_review_item_access_log",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_log_id", "clinic_id"],
            ["event_log.id", "event_log.clinic_id"],
            name="fk_audit_review_item_event_log",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_audit_review_item_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_audit_review_item_added_by",
        ),
    )
