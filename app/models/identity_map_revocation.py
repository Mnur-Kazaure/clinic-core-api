# app/models/identity_map_revocation.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IdentityMapRevocation(Base):
    __tablename__ = "identity_map_revocations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    map_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    revoked_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["map_id", "clinic_id"],
            ["patient_identity_map.id", "patient_identity_map.clinic_id"],
            name="fk_identity_revocation_map",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["identity_cases.id", "identity_cases.clinic_id"],
            name="fk_identity_revocation_case",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_revocation_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["revoked_by"],
            ["users.id"],
            name="fk_identity_revocation_by",
        ),
    )
