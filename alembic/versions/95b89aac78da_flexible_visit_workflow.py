"""flexible visit workflow

Revision ID: 95b89aac78da
Revises: cce96ad7bb91
Create Date: 2026-02-06 11:56:59.831139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95b89aac78da'
down_revision: Union[str, Sequence[str], None] = 'cce96ad7bb91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite requires batch mode for many ALTER TABLE operations.
    with op.batch_alter_table("visits") as batch:
        batch.add_column(
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )

    with op.batch_alter_table("visit_status_history") as batch:
        batch.add_column(
            sa.Column(
                "source",
                sa.String(length=20),
                nullable=False,
                server_default="manual",
            )
        )
        batch.add_column(sa.Column("reason_code", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("reason_text", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("pending_labs_count_snapshot", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column("unfulfilled_prescriptions_count_snapshot", sa.Integer(), nullable=True)
        )
        batch.add_column(sa.Column("idempotency_key", sa.String(length=255), nullable=True))

    # Idempotency keys must be globally unique per endpoint to be race-safe.
    with op.batch_alter_table("idempotency_keys") as batch:
        batch.create_unique_constraint(
            "uq_idempotency_keys_endpoint_key",
            ["endpoint", "key"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("idempotency_keys") as batch:
        batch.drop_constraint(
            "uq_idempotency_keys_endpoint_key",
            type_="unique",
        )

    with op.batch_alter_table("visit_status_history") as batch:
        batch.drop_column("idempotency_key")
        batch.drop_column("unfulfilled_prescriptions_count_snapshot")
        batch.drop_column("pending_labs_count_snapshot")
        batch.drop_column("reason_text")
        batch.drop_column("reason_code")
        batch.drop_column("source")

    with op.batch_alter_table("visits") as batch:
        batch.drop_column("version")
