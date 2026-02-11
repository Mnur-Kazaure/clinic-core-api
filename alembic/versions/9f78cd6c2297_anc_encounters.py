"""anc encounters

Revision ID: 9f78cd6c2297
Revises: 0e7e2a6389e4
Create Date: 2026-02-08 13:47:36.090386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f78cd6c2297'
down_revision: Union[str, Sequence[str], None] = '0e7e2a6389e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        record_status_enum = postgresql.ENUM(
            "DRAFT",
            "SIGNED",
            "AMENDED",
            "VOIDED",
            name="record_status",
            create_type=False,
        )
    else:
        record_status_enum = sa.Enum(
            "DRAFT",
            "SIGNED",
            "AMENDED",
            "VOIDED",
            name="record_status",
        )

    op.create_table(
        "anc_encounters",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "record_status",
            record_status_enum,
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("fundus_height", sa.Text(), nullable=True),
        sa.Column("presentation_position", sa.Text(), nullable=True),
        sa.Column("presenting_part", sa.Text(), nullable=True),
        sa.Column("foetal_heart", sa.Text(), nullable=True),
        sa.Column("bp_systolic", sa.Integer(), nullable=True),
        sa.Column("bp_diastolic", sa.Integer(), nullable=True),
        sa.Column("urine", sa.Text(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("ref", sa.Text(), nullable=True),
        sa.Column("initial", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(record_status != 'VOIDED') OR (void_reason IS NOT NULL)",
            name="ck_anc_encounters_void_reason",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_anc_encounters_visit_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["episode_id", "clinic_id"],
            ["pregnancy_episodes.id", "pregnancy_episodes.clinic_id"],
            name="fk_anc_encounters_episode_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_anc_encounters_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            name="fk_anc_encounters_recorded_by",
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_anc_encounters_id_clinic"),
        sa.UniqueConstraint("clinic_id", "visit_id", name="uq_anc_encounters_visit_clinic"),
    )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION anc_encounters_block_update_signed()
            RETURNS trigger AS $$
            BEGIN
                IF OLD.record_status = 'VOIDED' THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;
                IF OLD.record_status = 'SIGNED' AND (
                    NEW.record_status <> 'VOIDED' OR NEW.void_reason IS NULL OR
                    NEW.visit_id <> OLD.visit_id OR
                    NEW.clinic_id <> OLD.clinic_id OR
                    NEW.episode_id <> OLD.episode_id OR
                    NEW.recorded_by <> OLD.recorded_by OR
                    NEW.recorded_at <> OLD.recorded_at OR
                    NEW.fundus_height <> OLD.fundus_height OR
                    NEW.presentation_position <> OLD.presentation_position OR
                    NEW.presenting_part <> OLD.presenting_part OR
                    NEW.foetal_heart <> OLD.foetal_heart OR
                    NEW.bp_systolic <> OLD.bp_systolic OR
                    NEW.bp_diastolic <> OLD.bp_diastolic OR
                    NEW.urine <> OLD.urine OR
                    NEW.weight_kg <> OLD.weight_kg OR
                    NEW.remarks <> OLD.remarks OR
                    NEW.ref <> OLD.ref OR
                    NEW.initial <> OLD.initial OR
                    NEW.signed_at <> OLD.signed_at
                ) THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION anc_encounters_block_delete_signed()
            RETURNS trigger AS $$
            BEGIN
                IF OLD.record_status = 'SIGNED' THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER anc_encounters_block_update_signed
            BEFORE UPDATE ON anc_encounters
            FOR EACH ROW
            EXECUTE FUNCTION anc_encounters_block_update_signed();
            """
        )
        op.execute(
            """
            CREATE TRIGGER anc_encounters_block_delete_signed
            BEFORE DELETE ON anc_encounters
            FOR EACH ROW
            EXECUTE FUNCTION anc_encounters_block_delete_signed();
            """
        )
    else:
        op.execute(
            """
            CREATE TRIGGER anc_encounters_block_update_signed
            BEFORE UPDATE ON anc_encounters
            WHEN OLD.record_status = 'SIGNED'
            BEGIN
                SELECT RAISE(FAIL, 'signed record immutable');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER anc_encounters_block_delete_signed
            BEFORE DELETE ON anc_encounters
            WHEN OLD.record_status = 'SIGNED'
            BEGIN
                SELECT RAISE(FAIL, 'signed record immutable');
            END;
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS anc_encounters_block_delete_signed ON anc_encounters")
        op.execute("DROP TRIGGER IF EXISTS anc_encounters_block_update_signed ON anc_encounters")
        op.execute("DROP FUNCTION IF EXISTS anc_encounters_block_update_signed()")
        op.execute("DROP FUNCTION IF EXISTS anc_encounters_block_delete_signed()")
    else:
        op.execute("DROP TRIGGER IF EXISTS anc_encounters_block_update_signed")
        op.execute("DROP TRIGGER IF EXISTS anc_encounters_block_delete_signed")

    op.drop_table("anc_encounters")
