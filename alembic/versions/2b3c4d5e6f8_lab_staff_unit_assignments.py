"""lab staff roles and unit assignments for admin governance

Revision ID: 2b3c4d5e6f8
Revises: 1a2b3c4d5e7
Create Date: 2026-03-17 11:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f8"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("default_lab_unit_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_default_lab_unit",
        "users",
        "service_lines",
        ["default_lab_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_users_default_lab_unit_id",
        "users",
        ["default_lab_unit_id"],
    )

    op.create_table(
        "lab_user_unit_accesses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("service_line_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_lab_user_unit_accesses_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_lab_user_unit_accesses_service_line",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "service_line_id",
            name="uq_lab_user_unit_accesses_user_service_line",
        ),
    )
    op.create_index(
        "ix_lab_user_unit_accesses_user_id",
        "lab_user_unit_accesses",
        ["user_id"],
    )
    op.create_index(
        "ix_lab_user_unit_accesses_service_line_id",
        "lab_user_unit_accesses",
        ["service_line_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lab_user_unit_accesses_service_line_id",
        table_name="lab_user_unit_accesses",
    )
    op.drop_index(
        "ix_lab_user_unit_accesses_user_id",
        table_name="lab_user_unit_accesses",
    )
    op.drop_table("lab_user_unit_accesses")
    op.drop_index("ix_users_default_lab_unit_id", table_name="users")
    op.drop_constraint("fk_users_default_lab_unit", "users", type_="foreignkey")
    op.drop_column("users", "default_lab_unit_id")
