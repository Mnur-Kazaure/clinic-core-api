"""pharmacy return request timestamps catchup

Revision ID: h8c9d0e1f2a6
Revises: g7b8c9d0e1f5
Create Date: 2026-03-27 12:24:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2a6"
down_revision: Union[str, Sequence[str], None] = "g7b8c9d0e1f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "pharmacy_return_requests"):
        return

    if not _has_column(inspector, "pharmacy_return_requests", "created_at"):
        op.add_column(
            "pharmacy_return_requests",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    if not _has_column(inspector, "pharmacy_return_requests", "updated_at"):
        op.add_column(
            "pharmacy_return_requests",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )


def downgrade() -> None:
    return
