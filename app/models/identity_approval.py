# app/models/identity_approval.py
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKeyConstraint, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import IdentityApprovalRole, IdentityApprovalDecision


class IdentityApproval(Base):
    __tablename__ = "identity_approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    approver_role: Mapped[IdentityApprovalRole] = mapped_column(
        Enum(IdentityApprovalRole, name="identity_approval_role"),
        nullable=False,
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    decision: Mapped[IdentityApprovalDecision] = mapped_column(
        Enum(IdentityApprovalDecision, name="identity_approval_decision"),
        nullable=False,
    )
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["identity_cases.id", "identity_cases.clinic_id"],
            name="fk_identity_approval_case",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_approval_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["approver_id"],
            ["users.id"],
            name="fk_identity_approval_approver",
        ),
    )
