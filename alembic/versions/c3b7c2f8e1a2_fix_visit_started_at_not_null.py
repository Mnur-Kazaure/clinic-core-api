"""fix visit started_at not null

Revision ID: c3b7c2f8e1a2
Revises: d17d34da2ff1
Create Date: 2026-01-16 06:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3b7c2f8e1a2"
down_revision: Union[str, Sequence[str], None] = "d17d34da2ff1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE visits SET started_at = created_at WHERE started_at IS NULL")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("visits") as batch:
            batch.alter_column(
                "started_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            )
    else:
        op.alter_column(
            "visits",
            "started_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("visits") as batch:
            batch.alter_column(
                "started_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=True,
                server_default=None,
            )
    else:
        op.alter_column(
            "visits",
            "started_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
            server_default=None,
        )
