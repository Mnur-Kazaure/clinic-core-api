"""add visit service line

Revision ID: 43dad626f6b7
Revises: ad12ef34ab56
Create Date: 2026-02-08 13:38:06.372789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


SERVICE_LINES = ("OPD", "ANC", "MATERNITY")


# revision identifiers, used by Alembic.
revision: str = '43dad626f6b7'
down_revision: Union[str, Sequence[str], None] = 'ad12ef34ab56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        service_line_enum = postgresql.ENUM(
            *SERVICE_LINES,
            name="visit_service_line",
            create_type=False,
        )
        service_line_enum.create(bind, checkfirst=True)
    else:
        service_line_enum = sa.Enum(*SERVICE_LINES, name="visit_service_line")

    with op.batch_alter_table("visits") as batch:
        batch.add_column(
            sa.Column(
                "service_line",
                service_line_enum,
                nullable=False,
                server_default="OPD",
            )
        )

    op.create_index(
        "ix_visits_service_line_status",
        "visits",
        ["clinic_id", "service_line", "status"],
    )
    op.create_index(
        "ix_visits_service_line_owner_status",
        "visits",
        ["clinic_id", "service_line", "assigned_doctor_id", "status"],
    )
    op.create_index(
        "ix_visits_service_line_started_at",
        "visits",
        ["clinic_id", "service_line", "started_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.drop_index("ix_visits_service_line_started_at", table_name="visits")
    op.drop_index("ix_visits_service_line_owner_status", table_name="visits")
    op.drop_index("ix_visits_service_line_status", table_name="visits")

    with op.batch_alter_table("visits") as batch:
        batch.drop_column("service_line")

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        service_line_enum = postgresql.ENUM(
            *SERVICE_LINES,
            name="visit_service_line",
            create_type=False,
        )
        service_line_enum.drop(bind, checkfirst=True)
