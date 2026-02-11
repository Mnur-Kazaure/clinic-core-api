"""anc previous pregnancies

Revision ID: 0e7e2a6389e4
Revises: d423f3c6249b
Create Date: 2026-02-08 13:46:10.444250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e7e2a6389e4'
down_revision: Union[str, Sequence[str], None] = 'd423f3c6249b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.create_table(
        "pregnancy_previous_pregnancies",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Text(), nullable=True),
        sa.Column("antenatal_complications", sa.Text(), nullable=True),
        sa.Column("labour", sa.Text(), nullable=True),
        sa.Column("age_alive", sa.Integer(), nullable=True),
        sa.Column("age_dead", sa.Integer(), nullable=True),
        sa.Column("cause_of_death", sa.Text(), nullable=True),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["episode_id", "clinic_id"],
            ["pregnancy_episodes.id", "pregnancy_episodes.clinic_id"],
            name="fk_prev_preg_episode_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_prev_preg_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_prev_preg_added_by",
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_prev_preg_id_clinic"),
    )

    op.create_index(
        "ix_prev_preg_episode_added_at",
        "pregnancy_previous_pregnancies",
        ["episode_id", "added_at"],
    )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prev_preg_block_update_delete()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'previous pregnancies are append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER prev_preg_block_update
            BEFORE UPDATE ON pregnancy_previous_pregnancies
            FOR EACH ROW
            EXECUTE FUNCTION prev_preg_block_update_delete();
            """
        )
        op.execute(
            """
            CREATE TRIGGER prev_preg_block_delete
            BEFORE DELETE ON pregnancy_previous_pregnancies
            FOR EACH ROW
            EXECUTE FUNCTION prev_preg_block_update_delete();
            """
        )
    else:
        op.execute(
            """
            CREATE TRIGGER prev_preg_block_update
            BEFORE UPDATE ON pregnancy_previous_pregnancies
            BEGIN
                SELECT RAISE(FAIL, 'previous pregnancies are append-only');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER prev_preg_block_delete
            BEFORE DELETE ON pregnancy_previous_pregnancies
            BEGIN
                SELECT RAISE(FAIL, 'previous pregnancies are append-only');
            END;
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS prev_preg_block_delete ON pregnancy_previous_pregnancies")
        op.execute("DROP TRIGGER IF EXISTS prev_preg_block_update ON pregnancy_previous_pregnancies")
        op.execute("DROP FUNCTION IF EXISTS prev_preg_block_update_delete()")
    else:
        op.execute("DROP TRIGGER IF EXISTS prev_preg_block_update")
        op.execute("DROP TRIGGER IF EXISTS prev_preg_block_delete")

    op.drop_index("ix_prev_preg_episode_added_at", table_name="pregnancy_previous_pregnancies")
    op.drop_table("pregnancy_previous_pregnancies")
