"""enforce bed inventory uniqueness

Revision ID: 8b2c3d4e5f6a
Revises: 7a1b2c3d4e5f
Create Date: 2026-02-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "7a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    ward_uq = {uq["name"] for uq in inspector.get_unique_constraints("wards")}
    if "uq_wards_clinic_name" not in ward_uq:
        op.create_unique_constraint(
            "uq_wards_clinic_name",
            "wards",
            ["clinic_id", "name"],
        )

    bed_uq = {uq["name"] for uq in inspector.get_unique_constraints("beds")}
    if "uq_beds_clinic_ward_label" not in bed_uq:
        op.create_unique_constraint(
            "uq_beds_clinic_ward_label",
            "beds",
            ["clinic_id", "ward_id", "bed_label"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    bed_uq = {uq["name"] for uq in inspector.get_unique_constraints("beds")}
    if "uq_beds_clinic_ward_label" in bed_uq:
        op.drop_constraint(
            "uq_beds_clinic_ward_label",
            "beds",
            type_="unique",
        )

    ward_uq = {uq["name"] for uq in inspector.get_unique_constraints("wards")}
    if "uq_wards_clinic_name" in ward_uq:
        op.drop_constraint(
            "uq_wards_clinic_name",
            "wards",
            type_="unique",
        )
