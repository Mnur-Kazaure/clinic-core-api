"""add registration fee config + allow registration fee charges

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9a0b1c2d3e4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column(
        "clinics",
        sa.Column("registration_fee_minor", sa.BigInteger(), nullable=True, server_default="0"),
    )
    op.add_column(
        "clinics",
        sa.Column("registration_fee_required", sa.Boolean(), nullable=True, server_default=sa.true()),
    )
    op.execute("UPDATE clinics SET registration_fee_minor=0 WHERE registration_fee_minor IS NULL")
    op.execute(
        "UPDATE clinics SET registration_fee_required=TRUE WHERE registration_fee_required IS NULL"
    )
    if dialect == "postgresql":
        op.execute("ALTER TABLE clinics ALTER COLUMN registration_fee_minor SET NOT NULL")
        op.execute("ALTER TABLE clinics ALTER COLUMN registration_fee_required SET NOT NULL")
    else:
        with op.batch_alter_table("clinics") as batch:
            batch.alter_column("registration_fee_minor", nullable=False)
            batch.alter_column("registration_fee_required", nullable=False)

    if dialect == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                "ALTER TYPE billing_reason_code ADD VALUE IF NOT EXISTS 'REGISTRATION_FEE'"
            )

    context_rule = (
        "(entry_type IN ('PAYMENT','REFUND','REVERSAL')) OR "
        "(entry_type IN ('CHARGE','ADJUSTMENT','WRITE_OFF') AND "
        "(visit_id IS NOT NULL OR admission_id IS NOT NULL)) OR "
        "(entry_type = 'CHARGE' AND reason_code = 'REGISTRATION_FEE')"
    )

    if dialect == "postgresql":
        op.drop_constraint(
            "ck_billing_entry_context",
            "billing_ledger_entries",
            type_="check",
        )
        op.create_check_constraint(
            "ck_billing_entry_context",
            "billing_ledger_entries",
            context_rule,
        )
    else:
        with op.batch_alter_table("billing_ledger_entries") as batch:
            batch.drop_constraint("ck_billing_entry_context", type_="check")
            batch.create_check_constraint("ck_billing_entry_context", context_rule)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    old_rule = (
        "(entry_type IN ('CHARGE','ADJUSTMENT','WRITE_OFF') AND "
        "(visit_id IS NOT NULL OR admission_id IS NOT NULL)) OR "
        "(entry_type IN ('PAYMENT','REFUND','REVERSAL'))"
    )

    if dialect == "postgresql":
        op.drop_constraint(
            "ck_billing_entry_context",
            "billing_ledger_entries",
            type_="check",
        )
        op.create_check_constraint(
            "ck_billing_entry_context",
            "billing_ledger_entries",
            old_rule,
        )
    else:
        with op.batch_alter_table("billing_ledger_entries") as batch:
            batch.drop_constraint("ck_billing_entry_context", type_="check")
            batch.create_check_constraint("ck_billing_entry_context", old_rule)

    if dialect == "postgresql":
        op.execute("ALTER TABLE clinics ALTER COLUMN registration_fee_required DROP NOT NULL")
        op.execute("ALTER TABLE clinics ALTER COLUMN registration_fee_minor DROP NOT NULL")
    else:
        with op.batch_alter_table("clinics") as batch:
            batch.alter_column("registration_fee_required", nullable=True)
            batch.alter_column("registration_fee_minor", nullable=True)

    op.drop_column("clinics", "registration_fee_required")
    op.drop_column("clinics", "registration_fee_minor")
