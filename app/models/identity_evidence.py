# app/models/identity_evidence.py
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKeyConstraint, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import IdentityEvidenceType


class IdentityEvidence(Base):
    __tablename__ = "identity_evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    evidence_type: Mapped[IdentityEvidenceType] = mapped_column(
        Enum(IdentityEvidenceType, name="identity_evidence_type"),
        nullable=False,
    )
    ref: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["identity_cases.id", "identity_cases.clinic_id"],
            name="fk_identity_evidence_case",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_evidence_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_identity_evidence_added_by",
        ),
    )
