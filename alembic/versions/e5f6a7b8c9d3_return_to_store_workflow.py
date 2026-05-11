"""return to store workflow

Revision ID: e5f6a7b8c9d3
Revises: d4e5f6a7b8c2
Create Date: 2026-03-27 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e5f6a7b8c9d3"
down_revision = "d4e5f6a7b8c2"
branch_labels = None
depends_on = None


pharmacy_return_request_status = postgresql.ENUM(
    "RETURN_REQUESTED",
    "RETURN_PENDING_STORE_REVIEW",
    "RETURN_ACCEPTED",
    "RETURN_REJECTED",
    "RETURN_RECEIVED",
    "RETURN_CLOSED",
    name="pharmacy_return_request_status",
)

pharmacy_return_reason_code = postgresql.ENUM(
    "EXCESS_UNUSED",
    "WRONG_ISSUE",
    "DAMAGED_ON_RECEIPT",
    "EXPIRED_AT_UNIT",
    "UNIT_TRANSFER_CORRECTION",
    "OTHER",
    name="pharmacy_return_reason_code",
)


def upgrade() -> None:
    bind = op.get_bind()
    pharmacy_return_request_status.create(bind, checkfirst=True)
    pharmacy_return_reason_code.create(bind, checkfirst=True)

    op.create_table(
        "pharmacy_return_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("issue_voucher_id", sa.UUID(), nullable=False),
        sa.Column("issue_voucher_item_id", sa.UUID(), nullable=False),
        sa.Column("refill_request_id", sa.UUID(), nullable=True),
        sa.Column("store_unit_id", sa.UUID(), nullable=False),
        sa.Column("returning_unit_id", sa.UUID(), nullable=False),
        sa.Column("inventory_item_id", sa.UUID(), nullable=False),
        sa.Column("batch_number", sa.String(length=80), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("original_issued_quantity", sa.Integer(), nullable=False),
        sa.Column("quantity_already_returned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity_requested", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_issued_balance", sa.Integer(), nullable=False),
        sa.Column(
            "reason_code",
            postgresql.ENUM(
                "EXCESS_UNUSED",
                "WRONG_ISSUE",
                "DAMAGED_ON_RECEIPT",
                "EXPIRED_AT_UNIT",
                "UNIT_TRANSFER_CORRECTION",
                "OTHER",
                name="pharmacy_return_reason_code",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("reason_note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "RETURN_REQUESTED",
                "RETURN_PENDING_STORE_REVIEW",
                "RETURN_ACCEPTED",
                "RETURN_REJECTED",
                "RETURN_RECEIVED",
                "RETURN_CLOSED",
                name="pharmacy_return_request_status",
                create_type=False,
            ),
            nullable=False,
            server_default="RETURN_PENDING_STORE_REVIEW",
        ),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("received_by", sa.UUID(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receive_note", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_pharmacy_return_requests_clinic", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_voucher_id"], ["pharmacy_issue_vouchers.id"], name="fk_pharmacy_return_requests_voucher", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_voucher_item_id"], ["pharmacy_issue_voucher_items.id"], name="fk_pharmacy_return_requests_voucher_item", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["refill_request_id"], ["pharmacy_refill_requests.id"], name="fk_pharmacy_return_requests_refill_request", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["store_unit_id"], ["service_lines.id"], name="fk_pharmacy_return_requests_store_unit", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["returning_unit_id"], ["service_lines.id"], name="fk_pharmacy_return_requests_returning_unit", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["pharmacy_inventory_items.id"], name="fk_pharmacy_return_requests_inventory_item", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], name="fk_pharmacy_return_requests_requested_by", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_pharmacy_return_requests_reviewed_by", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["received_by"], ["users.id"], name="fk_pharmacy_return_requests_received_by", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "clinic_id", name="uq_pharmacy_return_requests_id_clinic"),
        sa.CheckConstraint("original_issued_quantity > 0", name="ck_pharmacy_return_requests_original_issued_positive"),
        sa.CheckConstraint("quantity_requested > 0", name="ck_pharmacy_return_requests_requested_positive"),
        sa.CheckConstraint("quantity_already_returned >= 0", name="ck_pharmacy_return_requests_already_returned_non_negative"),
        sa.CheckConstraint("quantity_received >= 0 AND quantity_received <= quantity_requested", name="ck_pharmacy_return_requests_received_range"),
        sa.CheckConstraint("remaining_issued_balance >= 0", name="ck_pharmacy_return_requests_remaining_non_negative"),
    )
    op.create_index(
        "ix_pharmacy_return_requests_voucher_item_status",
        "pharmacy_return_requests",
        ["issue_voucher_item_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_pharmacy_return_requests_returning_unit_status",
        "pharmacy_return_requests",
        ["returning_unit_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_pharmacy_return_requests_store_unit_status",
        "pharmacy_return_requests",
        ["store_unit_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pharmacy_return_requests_store_unit_status", table_name="pharmacy_return_requests")
    op.drop_index("ix_pharmacy_return_requests_returning_unit_status", table_name="pharmacy_return_requests")
    op.drop_index("ix_pharmacy_return_requests_voucher_item_status", table_name="pharmacy_return_requests")
    op.drop_table("pharmacy_return_requests")

    bind = op.get_bind()
    pharmacy_return_reason_code.drop(bind, checkfirst=True)
    pharmacy_return_request_status.drop(bind, checkfirst=True)
