"""pharmacy HOD and store role split

Revision ID: a1b2c3d4e5f6
Revises: 9b7a6c5d4e3f
Create Date: 2026-03-23 20:25:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9b7a6c5d4e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET role = 'PHARMACY_HOD'
            WHERE role = 'PHARMACY_MANAGER'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET role = 'PHARMACY_MANAGER'
            WHERE role = 'PHARMACY_HOD'
            """
        )
    )
