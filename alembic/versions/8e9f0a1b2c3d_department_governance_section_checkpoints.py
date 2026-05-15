"""add department governance section checkpoints

Revision ID: 8e9f0a1b2c3d
Revises: 7d8e9f0a1b2c
Create Date: 2026-03-19 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e9f0a1b2c3d"
down_revision: Union[str, Sequence[str], None] = "7d8e9f0a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "department_governance_section_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("workspace_key", sa.String(length=64), nullable=False),
        sa.Column("section_key", sa.String(length=64), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_department_governance_checkpoints_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_department_governance_checkpoints_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "clinic_id",
            "user_id",
            "workspace_key",
            "section_key",
            name="uq_department_governance_checkpoint_scope",
        ),
    )
    op.create_index(
        "ix_department_governance_checkpoints_scope",
        "department_governance_section_checkpoints",
        ["clinic_id", "user_id", "workspace_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_department_governance_checkpoints_scope",
        table_name="department_governance_section_checkpoints",
    )
    op.drop_table("department_governance_section_checkpoints")
