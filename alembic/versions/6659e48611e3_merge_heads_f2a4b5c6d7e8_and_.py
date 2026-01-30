"""merge heads f2a4b5c6d7e8 and f3c4d5e6a7b8

Revision ID: 6659e48611e3
Revises: f2a4b5c6d7e8, f3c4d5e6a7b8
Create Date: 2026-01-29 17:19:55.657875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6659e48611e3'
down_revision: Union[str, Sequence[str], None] = ('f2a4b5c6d7e8', 'f3c4d5e6a7b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
