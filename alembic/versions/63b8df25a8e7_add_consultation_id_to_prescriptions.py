"""add consultation_id to prescriptions

Revision ID: 63b8df25a8e7
Revises: b3f3b6af93e8
Create Date: 2026-01-06 11:04:40.462448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63b8df25a8e7'
down_revision: Union[str, Sequence[str], None] = 'b3f3b6af93e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
