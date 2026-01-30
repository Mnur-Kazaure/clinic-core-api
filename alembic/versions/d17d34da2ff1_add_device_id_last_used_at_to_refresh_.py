"""add_device_id_last_used_at_to_refresh_tokens

Revision ID: d17d34da2ff1
Revises: 63b8df25a8e7
Create Date: 2026-01-11 09:57:01.705704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd17d34da2ff1'
down_revision: Union[str, Sequence[str], None] = '63b8df25a8e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
