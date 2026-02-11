"""maternity delivery records

Revision ID: 41ca87889b69
Revises: 9f78cd6c2297
Create Date: 2026-02-08 13:48:56.169507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


DELIVERY_MODES = ("SVD", "C_SECTION", "ASSISTED", "UNKNOWN")
DELIVERY_OUTCOMES = ("LIVE_BIRTH", "STILLBIRTH", "NEONATAL_DEATH", "UNKNOWN")
BABY_SEX = ("MALE", "FEMALE", "UNKNOWN")


# revision identifiers, used by Alembic.
revision: str = '41ca87889b69'
down_revision: Union[str, Sequence[str], None] = '9f78cd6c2297'
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
        mode_enum = postgresql.ENUM(
            *DELIVERY_MODES,
            name="delivery_mode",
            create_type=False,
        )
        outcome_enum = postgresql.ENUM(
            *DELIVERY_OUTCOMES,
            name="delivery_outcome",
            create_type=False,
        )
        baby_sex_enum = postgresql.ENUM(
            *BABY_SEX,
            name="baby_sex",
            create_type=False,
        )
        mode_enum.create(bind, checkfirst=True)
        outcome_enum.create(bind, checkfirst=True)
        baby_sex_enum.create(bind, checkfirst=True)
    else:
        record_status_enum = sa.Enum(
            "DRAFT",
            "SIGNED",
            "AMENDED",
            "VOIDED",
            name="record_status",
        )
        mode_enum = sa.Enum(*DELIVERY_MODES, name="delivery_mode")
        outcome_enum = sa.Enum(*DELIVERY_OUTCOMES, name="delivery_outcome")
        baby_sex_enum = sa.Enum(*BABY_SEX, name="baby_sex")

    op.create_table(
        "maternity_delivery_records",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=True),
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
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "mode_of_delivery",
            mode_enum,
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column(
            "outcome",
            outcome_enum,
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column(
            "baby_sex",
            baby_sex_enum,
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("baby_weight_kg", sa.Numeric(), nullable=True),
        sa.Column("apgar_1", sa.Integer(), nullable=True),
        sa.Column("apgar_5", sa.Integer(), nullable=True),
        sa.Column("maternal_complications", sa.Text(), nullable=True),
        sa.Column("newborn_complications", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(record_status != 'VOIDED') OR (void_reason IS NOT NULL)",
            name="ck_maternity_delivery_void_reason",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_maternity_delivery_visit_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["episode_id", "clinic_id"],
            ["pregnancy_episodes.id", "pregnancy_episodes.clinic_id"],
            name="fk_maternity_delivery_episode_clinic",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_maternity_delivery_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            name="fk_maternity_delivery_recorded_by",
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_maternity_delivery_id_clinic"),
        sa.UniqueConstraint("clinic_id", "visit_id", name="uq_maternity_delivery_visit_clinic"),
    )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION maternity_delivery_block_update_signed()
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
                    NEW.delivered_at <> OLD.delivered_at OR
                    NEW.mode_of_delivery <> OLD.mode_of_delivery OR
                    NEW.outcome <> OLD.outcome OR
                    NEW.baby_sex <> OLD.baby_sex OR
                    NEW.baby_weight_kg <> OLD.baby_weight_kg OR
                    NEW.apgar_1 <> OLD.apgar_1 OR
                    NEW.apgar_5 <> OLD.apgar_5 OR
                    NEW.maternal_complications <> OLD.maternal_complications OR
                    NEW.newborn_complications <> OLD.newborn_complications OR
                    NEW.notes <> OLD.notes OR
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
            CREATE OR REPLACE FUNCTION maternity_delivery_block_delete_signed()
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
            CREATE TRIGGER maternity_delivery_block_update_signed
            BEFORE UPDATE ON maternity_delivery_records
            FOR EACH ROW
            EXECUTE FUNCTION maternity_delivery_block_update_signed();
            """
        )
        op.execute(
            """
            CREATE TRIGGER maternity_delivery_block_delete_signed
            BEFORE DELETE ON maternity_delivery_records
            FOR EACH ROW
            EXECUTE FUNCTION maternity_delivery_block_delete_signed();
            """
        )
    else:
        op.execute(
            """
            CREATE TRIGGER maternity_delivery_block_update_signed
            BEFORE UPDATE ON maternity_delivery_records
            WHEN OLD.record_status = 'SIGNED'
            BEGIN
                SELECT RAISE(FAIL, 'signed record immutable');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER maternity_delivery_block_delete_signed
            BEFORE DELETE ON maternity_delivery_records
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
        op.execute("DROP TRIGGER IF EXISTS maternity_delivery_block_delete_signed ON maternity_delivery_records")
        op.execute("DROP TRIGGER IF EXISTS maternity_delivery_block_update_signed ON maternity_delivery_records")
        op.execute("DROP FUNCTION IF EXISTS maternity_delivery_block_update_signed()")
        op.execute("DROP FUNCTION IF EXISTS maternity_delivery_block_delete_signed()")
    else:
        op.execute("DROP TRIGGER IF EXISTS maternity_delivery_block_update_signed")
        op.execute("DROP TRIGGER IF EXISTS maternity_delivery_block_delete_signed")

    op.drop_table("maternity_delivery_records")

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        mode_enum = postgresql.ENUM(*DELIVERY_MODES, name="delivery_mode", create_type=False)
        outcome_enum = postgresql.ENUM(*DELIVERY_OUTCOMES, name="delivery_outcome", create_type=False)
        baby_sex_enum = postgresql.ENUM(*BABY_SEX, name="baby_sex", create_type=False)
        mode_enum.drop(bind, checkfirst=True)
        outcome_enum.drop(bind, checkfirst=True)
        baby_sex_enum.drop(bind, checkfirst=True)
