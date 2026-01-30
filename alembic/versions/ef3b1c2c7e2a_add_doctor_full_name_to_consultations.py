"""add doctor full name to consultations

Revision ID: ef3b1c2c7e2a
Revises: 8e92d7b47ef4
Create Date: 2025-01-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ef3b1c2c7e2a"
down_revision = "8e92d7b47ef4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "consultations" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("consultations")}
    if "doctor_full_name" not in columns:
        op.add_column(
            "consultations",
            sa.Column("doctor_full_name", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "consultations" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("consultations")}
    if "doctor_full_name" in columns:
        op.drop_column("consultations", "doctor_full_name")
