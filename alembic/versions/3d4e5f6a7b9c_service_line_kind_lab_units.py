"""add explicit service line kind and backfill lab unit classification

Revision ID: 3d4e5f6a7b9c
Revises: 2b3c4d5e6f8
Create Date: 2026-03-18 11:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "3d4e5f6a7b9c"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


service_line_kind = postgresql.ENUM(
    "GENERAL",
    "LAB_UNIT",
    name="service_line_kind",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        service_line_kind.create(bind, checkfirst=True)

    op.add_column(
        "service_lines",
        sa.Column(
            "service_line_kind",
            service_line_kind if bind.dialect.name == "postgresql" else sa.String(length=32),
            nullable=False,
            server_default="GENERAL",
        ),
    )

    sources = [
        ("lab_user_unit_accesses", "service_line_id"),
        ("users", "default_lab_unit_id"),
        ("lab_requests", "target_unit_id"),
        ("lab_specimens", "target_unit_id"),
        ("lab_qc_runs", "unit_id"),
        ("lab_critical_alerts", "unit_id"),
        ("lab_test_catalog", "unit_id"),
    ]

    if bind.dialect.name == "postgresql":
        for table_name, column_name in sources:
            op.execute(
                sa.text(
                    f"""
                    UPDATE service_lines
                    SET service_line_kind = 'LAB_UNIT'::service_line_kind
                    WHERE id IN (
                        SELECT {column_name}
                        FROM {table_name}
                        WHERE {column_name} IS NOT NULL
                    )
                    """
                )
            )
    else:
        for table_name, column_name in sources:
            op.execute(
                sa.text(
                    f"""
                    UPDATE service_lines
                    SET service_line_kind = 'LAB_UNIT'
                    WHERE id IN (
                        SELECT {column_name}
                        FROM {table_name}
                        WHERE {column_name} IS NOT NULL
                    )
                    """
                )
            )


def downgrade() -> None:
    op.drop_column("service_lines", "service_line_kind")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        service_line_kind.drop(bind, checkfirst=True)
