"""pharmacy issue voucher nullability catchup

Revision ID: g7b8c9d0e1f5
Revises: f6a7b8c9d0e4
Create Date: 2026-03-27 12:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g7b8c9d0e1f5"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_foreign_key(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {row["name"] for row in inspector.get_foreign_keys(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "pharmacy_issue_vouchers"):
        return

    op.alter_column(
        "pharmacy_issue_vouchers",
        "issued_by",
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.alter_column(
        "pharmacy_issue_vouchers",
        "issued_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )

    bind.execute(
        sa.text(
            """
            UPDATE pharmacy_issue_vouchers
            SET issued_by = NULL,
                issued_at = NULL
            WHERE status IN ('PREPARED', 'DRAFT')
              AND dispatched_at IS NULL
            """
        )
    )

    inspector = sa.inspect(bind)
    if _has_foreign_key(
        inspector,
        "pharmacy_issue_vouchers",
        "fk_pharmacy_issue_vouchers_issued_by",
    ):
        op.drop_constraint(
            "fk_pharmacy_issue_vouchers_issued_by",
            "pharmacy_issue_vouchers",
            type_="foreignkey",
        )

    op.create_foreign_key(
        "fk_pharmacy_issue_vouchers_issued_by",
        "pharmacy_issue_vouchers",
        "users",
        ["issued_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    return
