"""add ward bed-range configuration fields

Revision ID: ab12cd34ef56
Revises: 9a4b5c6d7e8f, aa1b2c3d4e5f
Create Date: 2026-02-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ab12cd34ef56"
down_revision: Union[str, Sequence[str], None] = ("9a4b5c6d7e8f", "aa1b2c3d4e5f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("wards", sa.Column("bed_label_prefix", sa.String(length=32), nullable=True))
    op.add_column("wards", sa.Column("bed_label_padding", sa.Integer(), nullable=True))
    op.add_column("wards", sa.Column("bed_label_next", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("wards", "bed_label_next")
    op.drop_column("wards", "bed_label_padding")
    op.drop_column("wards", "bed_label_prefix")
