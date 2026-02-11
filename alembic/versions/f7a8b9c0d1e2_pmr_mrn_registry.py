"""pmr mrn registry

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-01-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MRN_STATUS_VALUES = ("ACTIVE", "RETIRED")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS citext")
        mrn_status = postgresql.ENUM(*MRN_STATUS_VALUES, name="mrn_status", create_type=False)
        mrn_status.create(bind, checkfirst=True)
        mrn_type = postgresql.CITEXT()
    else:
        mrn_status = sa.Enum(*MRN_STATUS_VALUES, name="mrn_status")
        mrn_type = sa.String(length=64)

    op.create_table(
        "clinic_mrn_sequences",
        sa.Column("clinic_id", sa.Uuid(), primary_key=True),
        sa.Column("prefix", sa.String(length=16), nullable=True),
        sa.Column("next_value", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("next_value >= 1", name="ck_clinic_mrn_sequences_next_value"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_clinic_mrn_sequences_clinic",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "patient_mrns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("mrn", mrn_type, nullable=False),
        sa.Column("status", mrn_status, nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_by", sa.Uuid(), nullable=False),
        sa.Column("check_digit", sa.String(length=1), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retire_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("clinic_id", "mrn", name="uq_patient_mrns_clinic_mrn"),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_patient_mrns_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_patient_mrns_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"],
            ["users.id"],
            name="fk_patient_mrns_issued_by",
        ),
    )

    if dialect == "postgresql":
        op.create_index(
            "uq_patient_mrns_active",
            "patient_mrns",
            ["clinic_id", "patient_id"],
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION patient_mrns_block_update()
            RETURNS trigger AS $$
            BEGIN
                IF OLD.mrn <> NEW.mrn
                    OR OLD.patient_id <> NEW.patient_id
                    OR OLD.clinic_id <> NEW.clinic_id
                    OR OLD.issued_at <> NEW.issued_at
                    OR OLD.issued_by <> NEW.issued_by
                    OR OLD.check_digit <> NEW.check_digit THEN
                    RAISE EXCEPTION 'patient MRN fields are immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER patient_mrns_block_update
            BEFORE UPDATE ON patient_mrns
            FOR EACH ROW
            EXECUTE FUNCTION patient_mrns_block_update();
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION patient_mrns_block_delete()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'patient MRNs are append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER patient_mrns_block_delete
            BEFORE DELETE ON patient_mrns
            FOR EACH ROW
            EXECUTE FUNCTION patient_mrns_block_delete();
            """
        )
    else:
        op.execute(
            """
            CREATE TRIGGER patient_mrns_block_update
            BEFORE UPDATE ON patient_mrns
            WHEN (OLD.mrn != NEW.mrn
                OR OLD.patient_id != NEW.patient_id
                OR OLD.clinic_id != NEW.clinic_id
                OR OLD.issued_at != NEW.issued_at
                OR OLD.issued_by != NEW.issued_by
                OR OLD.check_digit != NEW.check_digit)
            BEGIN
                SELECT RAISE(FAIL, 'patient MRN fields are immutable');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER patient_mrns_block_delete
            BEFORE DELETE ON patient_mrns
            BEGIN
                SELECT RAISE(FAIL, 'patient MRNs are append-only');
            END;
            """
        )

    op.create_index(
        "ix_patient_mrns_clinic_patient",
        "patient_mrns",
        ["clinic_id", "patient_id"],
    )
    op.create_index(
        "ix_patient_mrns_clinic_mrn",
        "patient_mrns",
        ["clinic_id", "mrn"],
    )
    op.create_index(
        "ix_identity_map_revocations_clinic_map",
        "identity_map_revocations",
        ["clinic_id", "map_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.drop_index("ix_identity_map_revocations_clinic_map", table_name="identity_map_revocations")
    op.drop_index("ix_patient_mrns_clinic_mrn", table_name="patient_mrns")
    op.drop_index("ix_patient_mrns_clinic_patient", table_name="patient_mrns")
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS patient_mrns_block_update ON patient_mrns")
        op.execute("DROP TRIGGER IF EXISTS patient_mrns_block_delete ON patient_mrns")
        op.execute("DROP FUNCTION IF EXISTS patient_mrns_block_update()")
        op.execute("DROP FUNCTION IF EXISTS patient_mrns_block_delete()")
        op.execute("DROP INDEX IF EXISTS uq_patient_mrns_active")
    else:
        op.execute("DROP TRIGGER IF EXISTS patient_mrns_block_update")
        op.execute("DROP TRIGGER IF EXISTS patient_mrns_block_delete")
    op.drop_table("patient_mrns")
    op.drop_table("clinic_mrn_sequences")
    if dialect == "postgresql":
        mrn_status = postgresql.ENUM(*MRN_STATUS_VALUES, name="mrn_status", create_type=False)
        mrn_status.drop(bind, checkfirst=True)
