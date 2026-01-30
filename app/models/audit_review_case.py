# app/models/audit_review_case.py
import uuid
from sqlalchemy import Enum, ForeignKeyConstraint, Text, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import AuditCaseStatus, AuditCaseSeverity, AuditCaseOutcome


class AuditReviewCase(Base):
    __tablename__ = "audit_review_cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[AuditCaseStatus] = mapped_column(
        Enum(AuditCaseStatus, name="audit_case_status"),
        nullable=False,
    )
    severity: Mapped[AuditCaseSeverity] = mapped_column(
        Enum(AuditCaseSeverity, name="audit_case_severity"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    closed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[AuditCaseOutcome | None] = mapped_column(
        Enum(AuditCaseOutcome, name="audit_case_outcome"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_audit_review_cases_id_clinic"),
        CheckConstraint(
            "(status != 'IN_REVIEW') OR (reviewed_by IS NOT NULL)",
            name="ck_audit_case_reviewed_by",
        ),
        CheckConstraint(
            "(status != 'CLOSED') OR (closed_by IS NOT NULL AND closed_at IS NOT NULL AND outcome IS NOT NULL)",
            name="ck_audit_case_closed_fields",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_audit_review_case_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_audit_review_case_created_by",
        ),
        ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_audit_review_case_reviewed_by",
        ),
        ForeignKeyConstraint(
            ["closed_by"],
            ["users.id"],
            name="fk_audit_review_case_closed_by",
        ),
    )
