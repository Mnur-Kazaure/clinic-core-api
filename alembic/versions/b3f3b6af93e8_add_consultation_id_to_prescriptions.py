"""add consultation_id to prescriptions

Revision ID: b3f3b6af93e8
Revises: d1a56b771f0d
Create Date: 2026-01-06 11:01:29.721623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f3b6af93e8'
down_revision: Union[str, Sequence[str], None] = 'd1a56b771f0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
