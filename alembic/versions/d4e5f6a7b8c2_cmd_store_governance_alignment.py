"""cmd store governance alignment

Revision ID: d4e5f6a7b8c2
Revises: c3d4e5f6a7b1
Create Date: 2026-03-26 21:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c2"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REFILL_REQUEST_STATUS_VALUES = (
    "AWAITING_CMD_APPROVAL",
    "ISSUE_PREPARATION_IN_PROGRESS",
    "BACKORDER_PENDING",
    "DISPATCHED",
    "ACKNOWLEDGED",
    "CLOSED",
)

ISSUE_VOUCHER_STATUS_VALUES = (
    "PREPARED",
    "DISPATCHED",
    "ACKNOWLEDGED",
    "CLOSED",
)


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_check_constraint(
    inspector: sa.Inspector, table_name: str, constraint_name: str
) -> bool:
    return constraint_name in {
        row["name"] for row in inspector.get_check_constraints(table_name)
    }


def _has_foreign_key(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {
        row["name"] for row in inspector.get_foreign_keys(table_name)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for value in REFILL_REQUEST_STATUS_VALUES:
                bind.execute(
                    sa.text(
                        "ALTER TYPE pharmacy_refill_request_status "
                        f"ADD VALUE IF NOT EXISTS '{value}'"
                    )
                )
            for value in ISSUE_VOUCHER_STATUS_VALUES:
                bind.execute(
                    sa.text(
                        "ALTER TYPE pharmacy_issue_voucher_status "
                        f"ADD VALUE IF NOT EXISTS '{value}'"
                    )
                )

    if _has_table(inspector, "pharmacy_inventory_items"):
        if not _has_column(inspector, "pharmacy_inventory_items", "classification"):
            op.add_column(
                "pharmacy_inventory_items",
                sa.Column(
                    "classification",
                    sa.String(length=24),
                    nullable=False,
                    server_default="DRUG",
                ),
            )
        if not _has_column(inspector, "pharmacy_inventory_items", "tracking_mode"):
            op.add_column(
                "pharmacy_inventory_items",
                sa.Column(
                    "tracking_mode",
                    sa.String(length=24),
                    nullable=False,
                    server_default="LOT_TRACKED",
                ),
            )
        if not _has_column(inspector, "pharmacy_inventory_items", "requires_expiry"):
            op.add_column(
                "pharmacy_inventory_items",
                sa.Column(
                    "requires_expiry",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
            )

        bind.execute(
            sa.text(
                """
                UPDATE pharmacy_inventory_items
                SET classification = COALESCE(classification, 'DRUG'),
                    tracking_mode = COALESCE(tracking_mode, 'LOT_TRACKED'),
                    requires_expiry = COALESCE(requires_expiry, true)
                """
            )
        )

        inspector = sa.inspect(bind)
        if not _has_check_constraint(
            inspector,
            "pharmacy_inventory_items",
            "ck_pharmacy_inventory_items_classification",
        ):
            op.create_check_constraint(
                "ck_pharmacy_inventory_items_classification",
                "pharmacy_inventory_items",
                "classification IN ('DRUG','CONSUMABLE','EQUIPMENT')",
            )
        if not _has_check_constraint(
            inspector,
            "pharmacy_inventory_items",
            "ck_pharmacy_inventory_items_tracking_mode",
        ):
            op.create_check_constraint(
                "ck_pharmacy_inventory_items_tracking_mode",
                "pharmacy_inventory_items",
                "tracking_mode IN ('LOT_TRACKED','QUANTITY_ONLY','SERIALIZED')",
            )

    if _has_table(inspector, "pharmacy_refill_requests"):
        if not _has_column(inspector, "pharmacy_refill_requests", "request_type"):
            op.add_column(
                "pharmacy_refill_requests",
                sa.Column(
                    "request_type",
                    sa.String(length=40),
                    nullable=False,
                    server_default="PHARMACY_REFILL",
                ),
            )
        if not _has_column(inspector, "pharmacy_refill_requests", "hod_visible_at"):
            op.add_column(
                "pharmacy_refill_requests",
                sa.Column("hod_visible_at", sa.DateTime(timezone=True), nullable=True),
            )

        bind.execute(
            sa.text(
                """
                UPDATE pharmacy_refill_requests
                SET request_type = COALESCE(request_type, 'PHARMACY_REFILL')
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE pharmacy_refill_requests
                SET status = 'AWAITING_CMD_APPROVAL'
                WHERE status = 'PENDING'
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE pharmacy_refill_requests
                SET hod_visible_at = COALESCE(hod_visible_at, reviewed_at)
                WHERE reviewed_at IS NOT NULL
                """
            )
        )

    if _has_table(inspector, "pharmacy_issue_vouchers"):
        if not _has_column(inspector, "pharmacy_issue_vouchers", "prepared_at"):
            op.add_column(
                "pharmacy_issue_vouchers",
                sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
            )
        if not _has_column(inspector, "pharmacy_issue_vouchers", "dispatched_by"):
            op.add_column(
                "pharmacy_issue_vouchers",
                sa.Column("dispatched_by", sa.UUID(), nullable=True),
            )
        if not _has_column(inspector, "pharmacy_issue_vouchers", "dispatched_at"):
            op.add_column(
                "pharmacy_issue_vouchers",
                sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
            )
        if not _has_column(inspector, "pharmacy_issue_vouchers", "closed_at"):
            op.add_column(
                "pharmacy_issue_vouchers",
                sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            )

        inspector = sa.inspect(bind)
        if not _has_foreign_key(
            inspector,
            "pharmacy_issue_vouchers",
            "fk_pharmacy_issue_vouchers_dispatched_by",
        ):
            op.create_foreign_key(
                "fk_pharmacy_issue_vouchers_dispatched_by",
                "pharmacy_issue_vouchers",
                "users",
                ["dispatched_by"],
                ["id"],
                ondelete="SET NULL",
            )

        bind.execute(
            sa.text(
                """
                UPDATE pharmacy_issue_vouchers
                SET prepared_at = COALESCE(prepared_at, issued_at, acknowledged_at, NOW())
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE pharmacy_issue_vouchers
                SET dispatched_at = COALESCE(dispatched_at, issued_at)
                WHERE status IN ('ISSUED', 'DISPATCHED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'ACKNOWLEDGED', 'CLOSED')
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE pharmacy_issue_vouchers
                SET closed_at = COALESCE(closed_at, acknowledged_at)
                WHERE status IN ('ACKNOWLEDGED', 'RECEIVED', 'CLOSED')
                """
            )
        )
        bind.execute(
            sa.text(
                """
                ALTER TABLE pharmacy_issue_vouchers
                ALTER COLUMN status SET DEFAULT 'PREPARED'
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "pharmacy_issue_vouchers"):
        bind.execute(
            sa.text(
                """
                ALTER TABLE pharmacy_issue_vouchers
                ALTER COLUMN status SET DEFAULT 'ISSUED'
                """
            )
        )
        inspector = sa.inspect(bind)
        if _has_foreign_key(
            inspector,
            "pharmacy_issue_vouchers",
            "fk_pharmacy_issue_vouchers_dispatched_by",
        ):
            op.drop_constraint(
                "fk_pharmacy_issue_vouchers_dispatched_by",
                "pharmacy_issue_vouchers",
                type_="foreignkey",
            )
        if _has_column(inspector, "pharmacy_issue_vouchers", "closed_at"):
            op.drop_column("pharmacy_issue_vouchers", "closed_at")
        if _has_column(inspector, "pharmacy_issue_vouchers", "dispatched_at"):
            op.drop_column("pharmacy_issue_vouchers", "dispatched_at")
        if _has_column(inspector, "pharmacy_issue_vouchers", "dispatched_by"):
            op.drop_column("pharmacy_issue_vouchers", "dispatched_by")
        if _has_column(inspector, "pharmacy_issue_vouchers", "prepared_at"):
            op.drop_column("pharmacy_issue_vouchers", "prepared_at")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pharmacy_refill_requests"):
        if _has_column(inspector, "pharmacy_refill_requests", "hod_visible_at"):
            op.drop_column("pharmacy_refill_requests", "hod_visible_at")
        if _has_column(inspector, "pharmacy_refill_requests", "request_type"):
            op.drop_column("pharmacy_refill_requests", "request_type")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pharmacy_inventory_items"):
        if _has_check_constraint(
            inspector,
            "pharmacy_inventory_items",
            "ck_pharmacy_inventory_items_tracking_mode",
        ):
            op.drop_constraint(
                "ck_pharmacy_inventory_items_tracking_mode",
                "pharmacy_inventory_items",
                type_="check",
            )
        if _has_check_constraint(
            inspector,
            "pharmacy_inventory_items",
            "ck_pharmacy_inventory_items_classification",
        ):
            op.drop_constraint(
                "ck_pharmacy_inventory_items_classification",
                "pharmacy_inventory_items",
                type_="check",
            )
        if _has_column(inspector, "pharmacy_inventory_items", "requires_expiry"):
            op.drop_column("pharmacy_inventory_items", "requires_expiry")
        if _has_column(inspector, "pharmacy_inventory_items", "tracking_mode"):
            op.drop_column("pharmacy_inventory_items", "tracking_mode")
        if _has_column(inspector, "pharmacy_inventory_items", "classification"):
            op.drop_column("pharmacy_inventory_items", "classification")
