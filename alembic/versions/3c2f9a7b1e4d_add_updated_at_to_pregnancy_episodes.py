"""add updated_at to pregnancy_episodes

Revision ID: 3c2f9a7b1e4d
Revises: 2f5161f9b611
Create Date: 2026-02-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c2f9a7b1e4d"
down_revision: Union[str, Sequence[str], None] = "2f5161f9b611"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("pregnancy_episodes")}
    if "updated_at" not in columns:
        op.add_column(
            "pregnancy_episodes",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("pregnancy_episodes")}
    if "updated_at" in columns:
        op.drop_column("pregnancy_episodes", "updated_at")

