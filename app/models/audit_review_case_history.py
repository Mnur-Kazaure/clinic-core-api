# app/models/audit_review_case_history.py
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKeyConstraint, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import AuditCaseStatus


class AuditReviewCaseHistory(Base):
    __tablename__ = "audit_review_case_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    from_status: Mapped[AuditCaseStatus | None] = mapped_column(
        Enum(AuditCaseStatus, name="audit_case_status"),
        nullable=True,
    )
    to_status: Mapped[AuditCaseStatus] = mapped_column(
        Enum(AuditCaseStatus, name="audit_case_status"),
        nullable=False,
    )
    changed_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["audit_review_cases.id", "audit_review_cases.clinic_id"],
            name="fk_audit_review_history_case",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_audit_review_history_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name="fk_audit_review_history_changed_by",
        ),
    )
