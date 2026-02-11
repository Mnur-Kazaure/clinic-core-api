"""visit intake flags

Revision ID: f8a9b0c1d2e3
Revises: f7a8b9c0d1e2
Create Date: 2026-02-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.create_table(
        "visit_intake_flags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("flagged", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("set_by", sa.Uuid(), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("char_length(reason) >= 3", name="ck_visit_intake_flags_reason"),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_visit_intake_flags_visit_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_visit_intake_flags_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["set_by"],
            ["users.id"],
            name="fk_visit_intake_flags_set_by",
        ),
    )

    op.create_index(
        "ix_visit_intake_flags_visit_set_at",
        "visit_intake_flags",
        ["visit_id", "set_at"],
    )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION visit_intake_flags_block_update_delete()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'visit intake flags are append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER visit_intake_flags_block_update
            BEFORE UPDATE ON visit_intake_flags
            FOR EACH ROW
            EXECUTE FUNCTION visit_intake_flags_block_update_delete();
            """
        )
        op.execute(
            """
            CREATE TRIGGER visit_intake_flags_block_delete
            BEFORE DELETE ON visit_intake_flags
            FOR EACH ROW
            EXECUTE FUNCTION visit_intake_flags_block_update_delete();
            """
        )
    else:
        op.execute(
            """
            CREATE TRIGGER visit_intake_flags_block_update
            BEFORE UPDATE ON visit_intake_flags
            BEGIN
                SELECT RAISE(FAIL, 'visit intake flags are append-only');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER visit_intake_flags_block_delete
            BEFORE DELETE ON visit_intake_flags
            BEGIN
                SELECT RAISE(FAIL, 'visit intake flags are append-only');
            END;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS visit_intake_flags_block_delete ON visit_intake_flags")
        op.execute("DROP TRIGGER IF EXISTS visit_intake_flags_block_update ON visit_intake_flags")
        op.execute("DROP FUNCTION IF EXISTS visit_intake_flags_block_update_delete()")
    else:
        op.execute("DROP TRIGGER IF EXISTS visit_intake_flags_block_update")
        op.execute("DROP TRIGGER IF EXISTS visit_intake_flags_block_delete")

    op.drop_index("ix_visit_intake_flags_visit_set_at", table_name="visit_intake_flags")
    op.drop_table("visit_intake_flags")
