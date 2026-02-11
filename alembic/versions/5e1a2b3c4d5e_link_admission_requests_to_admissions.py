"""link admission requests to admissions

Revision ID: 5e1a2b3c4d5e
Revises: 4d1f2a8c9b7e
Create Date: 2026-02-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "4d1f2a8c9b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("admission_requests")}
    if "admission_id" not in columns:
        op.add_column(
            "admission_requests",
            sa.Column("admission_id", sa.Uuid(), nullable=True),
        )

    fks = {fk["name"] for fk in inspector.get_foreign_keys("admission_requests")}
    if "fk_admission_requests_admission_clinic" not in fks:
        op.create_foreign_key(
            "fk_admission_requests_admission_clinic",
            "admission_requests",
            "admissions",
            ["admission_id", "clinic_id"],
            ["id", "clinic_id"],
            ondelete="SET NULL",
        )

    unique_constraints = {
        uq["name"] for uq in inspector.get_unique_constraints("admission_requests")
    }
    if "uq_admission_requests_admission_clinic" not in unique_constraints:
        op.create_unique_constraint(
            "uq_admission_requests_admission_clinic",
            "admission_requests",
            ["admission_id", "clinic_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    unique_constraints = {
        uq["name"] for uq in inspector.get_unique_constraints("admission_requests")
    }
    if "uq_admission_requests_admission_clinic" in unique_constraints:
        op.drop_constraint(
            "uq_admission_requests_admission_clinic",
            "admission_requests",
            type_="unique",
        )

    fks = {fk["name"] for fk in inspector.get_foreign_keys("admission_requests")}
    if "fk_admission_requests_admission_clinic" in fks:
        op.drop_constraint(
            "fk_admission_requests_admission_clinic",
            "admission_requests",
            type_="foreignkey",
        )

    columns = {column["name"] for column in inspector.get_columns("admission_requests")}
    if "admission_id" in columns:
        op.drop_column("admission_requests", "admission_id")
