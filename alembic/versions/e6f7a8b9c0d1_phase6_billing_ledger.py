"""phase6 billing ledger

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-01-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENTRY_TYPE_VALUES = (
    "CHARGE",
    "PAYMENT",
    "ADJUSTMENT",
    "REFUND",
    "WRITE_OFF",
    "REVERSAL",
)

REASON_CODE_VALUES = (
    "SERVICE",
    "LAB_TEST",
    "MEDICATION",
    "PROCEDURE",
    "CASH",
    "CARD",
    "TRANSFER",
    "INSURANCE",
    "DISCOUNT",
    "CORRECTION",
    "REFUND",
    "WRITE_OFF",
    "REVERSAL",
    "OTHER",
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        entry_type_enum = postgresql.ENUM(
            *ENTRY_TYPE_VALUES,
            name="billing_entry_type",
            create_type=False,
        )
        reason_code_enum = postgresql.ENUM(
            *REASON_CODE_VALUES,
            name="billing_reason_code",
            create_type=False,
        )
        entry_type_enum.create(bind, checkfirst=True)
        reason_code_enum.create(bind, checkfirst=True)
    else:
        entry_type_enum = sa.Enum(*ENTRY_TYPE_VALUES, name="billing_entry_type")
        reason_code_enum = sa.Enum(*REASON_CODE_VALUES, name="billing_reason_code")

    # clinics.billing_currency
    op.add_column(
        "clinics",
        sa.Column("billing_currency", sa.String(length=3), nullable=True, server_default="NGN"),
    )
    op.execute("UPDATE clinics SET billing_currency='NGN' WHERE billing_currency IS NULL")
    if dialect == "postgresql":
        op.execute("ALTER TABLE clinics ALTER COLUMN billing_currency SET NOT NULL")
    else:
        with op.batch_alter_table("clinics") as batch:
            batch.alter_column("billing_currency", nullable=False)

    op.create_table(
        "billing_ledger_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=True),
        sa.Column("admission_id", sa.Uuid(), nullable=True),
        sa.Column("entry_type", entry_type_enum, nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reason_code", reason_code_enum, nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=True),
        sa.Column("related_entry_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("actor_role", sa.String(length=50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("id", "clinic_id", name="uq_billing_ledger_id_clinic"),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_billing_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_billing_visit_clinic",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_billing_admission_clinic",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_entry_id", "clinic_id"],
            ["billing_ledger_entries.id", "billing_ledger_entries.clinic_id"],
            name="fk_billing_related_entry",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_billing_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_billing_actor",
        ),
        sa.CheckConstraint(
            "length(description) >= 3",
            name="ck_billing_description_length",
        ),
        sa.CheckConstraint(
            "amount_minor <> 0",
            name="ck_billing_amount_nonzero",
        ),
        sa.CheckConstraint(
            "(entry_type = 'CHARGE' AND amount_minor > 0) OR "
            "(entry_type = 'PAYMENT' AND amount_minor < 0) OR "
            "(entry_type = 'REFUND' AND amount_minor > 0) OR "
            "(entry_type = 'WRITE_OFF' AND amount_minor < 0) OR "
            "(entry_type IN ('ADJUSTMENT','REVERSAL') AND amount_minor <> 0)",
            name="ck_billing_entry_sign",
        ),
        sa.CheckConstraint(
            "(entry_type IN ('CHARGE','ADJUSTMENT','WRITE_OFF') AND (visit_id IS NOT NULL OR admission_id IS NOT NULL)) OR "
            "(entry_type IN ('PAYMENT','REFUND','REVERSAL'))",
            name="ck_billing_entry_context",
        ),
        sa.CheckConstraint(
            "(entry_type = 'REVERSAL' AND related_entry_id IS NOT NULL) OR "
            "(entry_type != 'REVERSAL' AND related_entry_id IS NULL)",
            name="ck_billing_reversal_link",
        ),
    )

    op.create_table(
        "charge_catalog",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("default_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("clinic_id", "code", name="uq_charge_catalog_code"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_charge_catalog_clinic",
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_billing_ledger_patient_time",
        "billing_ledger_entries",
        ["clinic_id", "patient_id", "occurred_at"],
    )
    op.create_index(
        "ix_billing_ledger_entry_type_time",
        "billing_ledger_entries",
        ["clinic_id", "entry_type", "occurred_at"],
    )

    if dialect == "postgresql":
        op.create_index(
            "ix_billing_ledger_visit",
            "billing_ledger_entries",
            ["clinic_id", "visit_id"],
            postgresql_where=sa.text("visit_id IS NOT NULL"),
        )
        op.create_index(
            "ix_billing_ledger_admission",
            "billing_ledger_entries",
            ["clinic_id", "admission_id"],
            postgresql_where=sa.text("admission_id IS NOT NULL"),
        )
        op.create_index(
            "uq_billing_external_ref",
            "billing_ledger_entries",
            ["clinic_id", "external_ref"],
            unique=True,
            postgresql_where=sa.text("external_ref IS NOT NULL"),
        )
        op.execute(
            """
CREATE OR REPLACE FUNCTION billing_ledger_entries_block_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'billing ledger is append-only';
END;
$$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
CREATE TRIGGER billing_ledger_entries_block_update
BEFORE UPDATE ON billing_ledger_entries
FOR EACH ROW EXECUTE FUNCTION billing_ledger_entries_block_mutation();
            """
        )
        op.execute(
            """
CREATE TRIGGER billing_ledger_entries_block_delete
BEFORE DELETE ON billing_ledger_entries
FOR EACH ROW EXECUTE FUNCTION billing_ledger_entries_block_mutation();
            """
        )
    else:
        op.create_index(
            "ix_billing_ledger_visit",
            "billing_ledger_entries",
            ["clinic_id", "visit_id"],
        )
        op.create_index(
            "ix_billing_ledger_admission",
            "billing_ledger_entries",
            ["clinic_id", "admission_id"],
        )
        op.create_index(
            "uq_billing_external_ref",
            "billing_ledger_entries",
            ["clinic_id", "external_ref"],
            unique=True,
        )
        op.execute(
            """
CREATE TRIGGER billing_ledger_entries_block_update
BEFORE UPDATE ON billing_ledger_entries
BEGIN
    SELECT RAISE(FAIL, 'billing ledger is append-only');
END;
            """
        )
        op.execute(
            """
CREATE TRIGGER billing_ledger_entries_block_delete
BEFORE DELETE ON billing_ledger_entries
BEGIN
    SELECT RAISE(FAIL, 'billing ledger is append-only');
END;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS billing_ledger_entries_block_update ON billing_ledger_entries")
        op.execute("DROP TRIGGER IF EXISTS billing_ledger_entries_block_delete ON billing_ledger_entries")
        op.execute("DROP FUNCTION IF EXISTS billing_ledger_entries_block_mutation")
    else:
        op.execute("DROP TRIGGER IF EXISTS billing_ledger_entries_block_update")
        op.execute("DROP TRIGGER IF EXISTS billing_ledger_entries_block_delete")

    op.drop_index("uq_billing_external_ref", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_admission", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_visit", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_entry_type_time", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_patient_time", table_name="billing_ledger_entries")

    op.drop_table("charge_catalog")
    op.drop_table("billing_ledger_entries")

    if dialect == "postgresql":
        op.execute("ALTER TABLE clinics ALTER COLUMN billing_currency DROP NOT NULL")
    else:
        with op.batch_alter_table("clinics") as batch:
            batch.alter_column("billing_currency", nullable=True)
    op.drop_column("clinics", "billing_currency")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS billing_reason_code")
        op.execute("DROP TYPE IF EXISTS billing_entry_type")
