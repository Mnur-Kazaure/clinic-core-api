import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKeyConstraint,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import FollowUpPriority, RecallIntervalUnit


class ConditionProfile(Base):
    __tablename__ = "condition_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    recall_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    default_interval_value: Mapped[int] = mapped_column(Integer, nullable=False)
    default_interval_unit: Mapped[RecallIntervalUnit] = mapped_column(
        Enum(RecallIntervalUnit, name="recall_interval_unit"),
        nullable=False,
    )
    default_priority: Mapped[FollowUpPriority] = mapped_column(
        Enum(FollowUpPriority, name="follow_up_priority"),
        nullable=False,
        default=FollowUpPriority.IMPORTANT,
        server_default=FollowUpPriority.IMPORTANT.value,
    )
    cooldown_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=90,
        server_default="90",
    )
    keyword_synonyms: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_condition_profiles_id_clinic"),
        UniqueConstraint("clinic_id", "code", name="uq_condition_profiles_clinic_code"),
        UniqueConstraint(
            "clinic_id",
            "display_name",
            name="uq_condition_profiles_clinic_display_name",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_condition_profiles_clinic_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_condition_profiles_created_by",
        ),
    )
