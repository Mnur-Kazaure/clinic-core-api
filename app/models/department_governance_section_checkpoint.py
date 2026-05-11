import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DepartmentGovernanceSectionCheckpoint(Base):
    __tablename__ = "department_governance_section_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workspace_key: Mapped[str] = mapped_column(String(64), nullable=False)
    section_key: Mapped[str] = mapped_column(String(64), nullable=False)
    last_viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "user_id",
            "workspace_key",
            "section_key",
            name="uq_department_governance_checkpoint_scope",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_department_governance_checkpoints_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_department_governance_checkpoints_user",
            ondelete="CASCADE",
        ),
    )
