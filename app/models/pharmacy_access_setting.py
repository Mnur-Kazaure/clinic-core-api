import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PharmacyAccessSetting(Base):
    __tablename__ = "pharmacy_access_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    inventory_mode: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="EDITABLE",
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            name="uq_pharmacy_access_settings_clinic",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_access_settings_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name="fk_pharmacy_access_settings_changed_by",
        ),
        CheckConstraint(
            "inventory_mode IN ('EDITABLE','READ_ONLY')",
            name="ck_pharmacy_access_settings_mode",
        ),
    )
