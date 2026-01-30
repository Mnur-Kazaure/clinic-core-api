# app/models/identity_case.py
import uuid

from sqlalchemy import Enum, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import IdentityCaseType, IdentityCaseStatus


class IdentityCase(Base):
    __tablename__ = "identity_cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    case_type: Mapped[IdentityCaseType] = mapped_column(
        Enum(IdentityCaseType, name="identity_case_type"),
        nullable=False,
    )
    status: Mapped[IdentityCaseStatus] = mapped_column(
        Enum(IdentityCaseStatus, name="identity_case_status"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    primary_patient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    target_patient_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_identity_cases_id_clinic"),
        ForeignKeyConstraint(
            ["primary_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_case_primary_patient",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["target_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_case_target_patient",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_case_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_identity_case_created_by",
        ),
    )
