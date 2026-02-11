"""maternity postnatal and family planning

Revision ID: 2f5161f9b611
Revises: 41ca87889b69
Create Date: 2026-02-08 13:50:35.723717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


POSTNATAL_SUBJECTS = ("MOTHER", "BABY")
FP_COMMODITIES = ("IMPLANT", "IUD", "INJECTABLE", "PILL", "CONDOM", "OTHER")


# revision identifiers, used by Alembic.
revision: str = '2f5161f9b611'
down_revision: Union[str, Sequence[str], None] = '41ca87889b69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        postnatal_subject_enum = postgresql.ENUM(
            *POSTNATAL_SUBJECTS,
            name="postnatal_subject",
            create_type=False,
        )
        fp_commodity_enum = postgresql.ENUM(
            *FP_COMMODITIES,
            name="fp_commodity",
            create_type=False,
        )
        postnatal_subject_enum.create(bind, checkfirst=True)
        fp_commodity_enum.create(bind, checkfirst=True)
    else:
        postnatal_subject_enum = sa.Enum(*POSTNATAL_SUBJECTS, name="postnatal_subject")
        fp_commodity_enum = sa.Enum(*FP_COMMODITIES, name="fp_commodity")

    op.create_table(
        "maternity_postnatal_notes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("subject", postnatal_subject_enum, nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("char_length(note) >= 3", name="ck_postnatal_note_min_len"),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_postnatal_notes_visit_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_postnatal_notes_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_postnatal_notes_added_by",
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_postnatal_notes_id_clinic"),
    )

    op.create_table(
        "family_planning_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("commodity", fp_commodity_enum, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_fp_events_visit_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_fp_events_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_fp_events_added_by",
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_fp_events_id_clinic"),
    )

    op.create_index(
        "ix_postnatal_notes_visit_added_at",
        "maternity_postnatal_notes",
        ["visit_id", "added_at"],
    )
    op.create_index(
        "ix_fp_events_visit_added_at",
        "family_planning_events",
        ["visit_id", "added_at"],
    )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION postnatal_notes_block_update_delete()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'postnatal notes are append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER postnatal_notes_block_update
            BEFORE UPDATE ON maternity_postnatal_notes
            FOR EACH ROW
            EXECUTE FUNCTION postnatal_notes_block_update_delete();
            """
        )
        op.execute(
            """
            CREATE TRIGGER postnatal_notes_block_delete
            BEFORE DELETE ON maternity_postnatal_notes
            FOR EACH ROW
            EXECUTE FUNCTION postnatal_notes_block_update_delete();
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION fp_events_block_update_delete()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'family planning events are append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER fp_events_block_update
            BEFORE UPDATE ON family_planning_events
            FOR EACH ROW
            EXECUTE FUNCTION fp_events_block_update_delete();
            """
        )
        op.execute(
            """
            CREATE TRIGGER fp_events_block_delete
            BEFORE DELETE ON family_planning_events
            FOR EACH ROW
            EXECUTE FUNCTION fp_events_block_update_delete();
            """
        )
    else:
        op.execute(
            """
            CREATE TRIGGER postnatal_notes_block_update
            BEFORE UPDATE ON maternity_postnatal_notes
            BEGIN
                SELECT RAISE(FAIL, 'postnatal notes are append-only');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER postnatal_notes_block_delete
            BEFORE DELETE ON maternity_postnatal_notes
            BEGIN
                SELECT RAISE(FAIL, 'postnatal notes are append-only');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER fp_events_block_update
            BEFORE UPDATE ON family_planning_events
            BEGIN
                SELECT RAISE(FAIL, 'family planning events are append-only');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER fp_events_block_delete
            BEFORE DELETE ON family_planning_events
            BEGIN
                SELECT RAISE(FAIL, 'family planning events are append-only');
            END;
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS fp_events_block_delete ON family_planning_events")
        op.execute("DROP TRIGGER IF EXISTS fp_events_block_update ON family_planning_events")
        op.execute("DROP FUNCTION IF EXISTS fp_events_block_update_delete()")
        op.execute("DROP TRIGGER IF EXISTS postnatal_notes_block_delete ON maternity_postnatal_notes")
        op.execute("DROP TRIGGER IF EXISTS postnatal_notes_block_update ON maternity_postnatal_notes")
        op.execute("DROP FUNCTION IF EXISTS postnatal_notes_block_update_delete()")
    else:
        op.execute("DROP TRIGGER IF EXISTS fp_events_block_update")
        op.execute("DROP TRIGGER IF EXISTS fp_events_block_delete")
        op.execute("DROP TRIGGER IF EXISTS postnatal_notes_block_update")
        op.execute("DROP TRIGGER IF EXISTS postnatal_notes_block_delete")

    op.drop_index("ix_fp_events_visit_added_at", table_name="family_planning_events")
    op.drop_index("ix_postnatal_notes_visit_added_at", table_name="maternity_postnatal_notes")
    op.drop_table("family_planning_events")
    op.drop_table("maternity_postnatal_notes")

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        postnatal_subject_enum = postgresql.ENUM(
            *POSTNATAL_SUBJECTS,
            name="postnatal_subject",
            create_type=False,
        )
        fp_commodity_enum = postgresql.ENUM(
            *FP_COMMODITIES,
            name="fp_commodity",
            create_type=False,
        )
        postnatal_subject_enum.drop(bind, checkfirst=True)
        fp_commodity_enum.drop(bind, checkfirst=True)
