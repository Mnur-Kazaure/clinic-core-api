"""finance ops: receipt sequence, refunds, reprint logs, cashier shifts

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-03-05 22:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "receipt_sequences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("prefix", sa.String(length=20), nullable=False, server_default="RCPT"),
        sa.Column("padding", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("last_number", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("reset_yearly", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("current_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("clinic_id", name="uq_receipt_sequences_clinic"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_receipt_sequences_clinic",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "receipt_reprint_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("reprinted_by", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reprinted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_receipt_reprint_logs_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id", "clinic_id"],
            ["payment_receipts.id", "payment_receipts.clinic_id"],
            name="fk_receipt_reprint_logs_receipt",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reprinted_by"],
            ["users.id"],
            name="fk_receipt_reprint_logs_reprinted_by",
        ),
    )
    op.create_index(
        "ix_receipt_reprint_logs_receipt_time",
        "receipt_reprint_logs",
        ["clinic_id", "receipt_id", "reprinted_at"],
    )

    op.create_table(
        "cashier_shifts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("cashier_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_float_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("closing_cash_minor", sa.BigInteger(), nullable=True),
        sa.Column("closing_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_cashier_shifts_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cashier_id"],
            ["users.id"],
            name="fk_cashier_shifts_cashier",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("status IN ('OPEN','CLOSED')", name="ck_cashier_shifts_status"),
        sa.CheckConstraint(
            "opening_float_minor >= 0",
            name="ck_cashier_shifts_opening_float_non_negative",
        ),
    )
    op.create_index(
        "ix_cashier_shifts_clinic_cashier_status",
        "cashier_shifts",
        ["clinic_id", "cashier_id", "status", "started_at"],
    )

    op.create_table(
        "billing_refunds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("billing_item_id", sa.Uuid(), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PROCESSED"),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("processed_by", sa.Uuid(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_billing_refunds_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id", "clinic_id"],
            ["payment_receipts.id", "payment_receipts.clinic_id"],
            name="fk_billing_refunds_receipt",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["billing_item_id", "clinic_id"],
            ["billing_items.id", "billing_items.clinic_id"],
            name="fk_billing_refunds_billing_item",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_billing_refunds_requested_by",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_billing_refunds_approved_by",
        ),
        sa.ForeignKeyConstraint(
            ["processed_by"],
            ["users.id"],
            name="fk_billing_refunds_processed_by",
        ),
        sa.CheckConstraint("amount_minor > 0", name="ck_billing_refunds_amount_positive"),
        sa.CheckConstraint(
            "status IN ('REQUESTED','PROCESSED','REJECTED')",
            name="ck_billing_refunds_status",
        ),
    )
    op.create_index(
        "ix_billing_refunds_status_requested",
        "billing_refunds",
        ["clinic_id", "status", "requested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_billing_refunds_status_requested", table_name="billing_refunds")
    op.drop_table("billing_refunds")

    op.drop_index("ix_cashier_shifts_clinic_cashier_status", table_name="cashier_shifts")
    op.drop_table("cashier_shifts")

    op.drop_index("ix_receipt_reprint_logs_receipt_time", table_name="receipt_reprint_logs")
    op.drop_table("receipt_reprint_logs")

    op.drop_table("receipt_sequences")
