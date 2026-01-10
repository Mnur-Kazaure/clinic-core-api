"""fix idempotency created_at default

Revision ID: d1a56b771f0d
Revises: bc08b2efdd7d
Create Date: 2026-01-03 17:56:53.010533
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "d1a56b771f0d"
down_revision: Union[str, Sequence[str], None] = "bc08b2efdd7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix idempotency_keys.created_at default to now()
    SAFE: no table drops, no enum changes
    """
    op.alter_column(
        "idempotency_keys",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        nullable=False,
    )


def downgrade() -> None:
    """
    Revert created_at default
    """
    op.alter_column(
        "idempotency_keys",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        server_default=None,
        nullable=False,
    )
