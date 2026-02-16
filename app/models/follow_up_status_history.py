import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import FollowUpStatus


class FollowUpStatusHistory(Base):
    __tablename__ = "follow_up_status_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    follow_up_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    old_status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, name="follow_up_status"),
        nullable=False,
    )
    new_status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, name="follow_up_status"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["follow_up_id"],
            ["follow_ups.id"],
            name="fk_follow_up_status_history_follow_up_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_follow_up_status_history_actor_user_id",
            ondelete="SET NULL",
        ),
    )
