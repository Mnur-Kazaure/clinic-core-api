"""add patients composite unique (id, clinic_id)

Revision ID: f2a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-01-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {uc["name"] for uc in inspector.get_unique_constraints("patients")}
    if "uq_patients_id_clinic" not in existing:
        op.create_unique_constraint("uq_patients_id_clinic", "patients", ["id", "clinic_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {uc["name"] for uc in inspector.get_unique_constraints("patients")}
    if "uq_patients_id_clinic" in existing:
        op.drop_constraint("uq_patients_id_clinic", "patients", type_="unique")
