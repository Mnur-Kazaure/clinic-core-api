"""pharmacy issue voucher status enum catchup

Revision ID: f6a7b8c9d0e4
Revises: e5f6a7b8c9d3
Create Date: 2026-03-27 12:18:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e4"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ISSUE_VOUCHER_STATUS_VALUES = (
    "DRAFT",
    "PREPARED",
    "ISSUED",
    "DISPATCHED",
    "ACKNOWLEDGED",
    "CLOSED",
    "PARTIALLY_RECEIVED",
    "RECEIVED",
    "CANCELLED",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        for value in ISSUE_VOUCHER_STATUS_VALUES:
            bind.execute(
                sa.text(
                    "ALTER TYPE pharmacy_issue_voucher_status "
                    f"ADD VALUE IF NOT EXISTS '{value}'"
                )
            )


def downgrade() -> None:
    return
