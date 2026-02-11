"""add lab request instructions

Revision ID: 2c0d54e1275a
Revises: fc1d2e3f4g5h
Create Date: 2026-02-02 18:46:10.153036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c0d54e1275a'
down_revision: Union[str, Sequence[str], None] = 'fc1d2e3f4g5h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "lab_requests",
        sa.Column("special_instructions", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("lab_requests", "special_instructions")
