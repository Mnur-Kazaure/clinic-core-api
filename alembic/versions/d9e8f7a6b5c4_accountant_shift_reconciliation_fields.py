"""accountant: cashier shift reconciliation fields

Revision ID: d9e8f7a6b5c4
Revises: c7d8e9f0a1b2
Create Date: 2026-03-06 00:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9e8f7a6b5c4"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cashier_shifts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reconciled_by", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.drop_constraint("ck_cashier_shifts_status", type_="check")
        batch_op.create_check_constraint(
            "ck_cashier_shifts_status",
            "status IN ('OPEN','CLOSED','RECONCILED')",
        )
        batch_op.create_foreign_key(
            "fk_cashier_shifts_reconciled_by",
            "users",
            ["reconciled_by"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("cashier_shifts", schema=None) as batch_op:
        batch_op.drop_constraint("fk_cashier_shifts_reconciled_by", type_="foreignkey")
        batch_op.drop_constraint("ck_cashier_shifts_status", type_="check")
        batch_op.create_check_constraint(
            "ck_cashier_shifts_status",
            "status IN ('OPEN','CLOSED')",
        )
        batch_op.drop_column("reconciled_at")
        batch_op.drop_column("reconciled_by")

