"""lab role access matrix

Revision ID: 4a5b6c7d8e9f
Revises: 3d4e5f6a7b9c
Create Date: 2026-03-18 18:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4a5b6c7d8e9f"
down_revision = "3d4e5f6a7b9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lab_test_config",
        sa.Column(
            "allows_scientist_verification",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "lab_test_config",
        sa.Column(
            "scientist_verification_restricted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "lab_results",
        sa.Column("amendment_reason", sa.String(length=255), nullable=True),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TYPE lab_specimen_rejection_reason_code ADD VALUE IF NOT EXISTS 'WRONG_LABEL'"
        )
        op.execute(
            "ALTER TYPE lab_specimen_rejection_reason_code ADD VALUE IF NOT EXISTS 'BROKEN_CONTAINER'"
        )
        op.execute(
            "ALTER TYPE lab_specimen_rejection_reason_code ADD VALUE IF NOT EXISTS 'MISSING_SAMPLE'"
        )


def downgrade() -> None:
    op.drop_column("lab_results", "amendment_reason")
    op.drop_column("lab_test_config", "scientist_verification_restricted")
    op.drop_column("lab_test_config", "allows_scientist_verification")
