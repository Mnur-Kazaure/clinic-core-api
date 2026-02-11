"""set registration fee default to 1000 NGN

Revision ID: fa0b1c2d3e4
Revises: f9a0b1c2d3e4
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


revision = "fa0b1c2d3e4"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE clinics
        SET registration_fee_minor = 100000
        WHERE registration_fee_required = TRUE
          AND registration_fee_minor = 0
        """
    )
    op.alter_column(
        "clinics",
        "registration_fee_minor",
        server_default=sa.text("100000"),
    )


def downgrade() -> None:
    op.alter_column(
        "clinics",
        "registration_fee_minor",
        server_default=sa.text("0"),
    )
