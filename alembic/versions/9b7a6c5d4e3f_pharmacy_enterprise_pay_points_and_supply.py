"""pharmacy enterprise pay points, routing, and supply workflow schema

Revision ID: 9b7a6c5d4e3f
Revises: 8e9f0a1b2c3d
Create Date: 2026-03-23 13:40:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.shared.enums import (
    PharmacyExceptionAuthorizationType,
    PharmacyIssueVoucherStatus,
    PharmacyPrescriptionWorkflowStatus,
    PharmacyRefillRequestStatus,
    PharmacyUnitCategory,
)


# revision identifiers, used by Alembic.
revision: str = "9b7a6c5d4e3f"
down_revision: Union[str, Sequence[str], None] = "8e9f0a1b2c3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum_values(enum_cls) -> list[str]:
    return [member.value for member in enum_cls]


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _fk_exists(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return fk_name in {fk["name"] for fk in inspector.get_foreign_keys(table_name)}


def _check_exists(inspector: sa.Inspector, table_name: str, check_name: str) -> bool:
    return check_name in {check["name"] for check in inspector.get_check_constraints(table_name)}


def _enum_type(bind, *, name: str, values: list[str]):
    if bind.dialect.name == "postgresql":
        enum_type = postgresql.ENUM(*values, name=name, create_type=False)
        enum_type.create(bind, checkfirst=True)
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _existing_enum_type(bind, *, name: str, values: list[str]):
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _create_cashier_pay_points(inspector: sa.Inspector) -> None:
    if _table_exists(inspector, "cashier_pay_points"):
        return

    op.create_table(
        "cashier_pay_points",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_cashier_pay_points_id_clinic"),
        sa.UniqueConstraint("clinic_id", "code", name="uq_cashier_pay_points_clinic_code"),
        sa.UniqueConstraint("clinic_id", "name", name="uq_cashier_pay_points_clinic_name"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_cashier_pay_points_clinic",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_cashier_pay_points_clinic_active_name",
        "cashier_pay_points",
        ["clinic_id", "is_active", "name"],
    )


def _create_cashier_pay_point_accesses(inspector: sa.Inspector) -> None:
    if _table_exists(inspector, "cashier_pay_point_accesses"):
        return

    op.create_table(
        "cashier_pay_point_accesses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("cashier_pay_point_id", sa.Uuid(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "id",
            "clinic_id",
            name="uq_cashier_pay_point_accesses_id_clinic",
        ),
        sa.UniqueConstraint(
            "user_id",
            "cashier_pay_point_id",
            name="uq_cashier_pay_point_accesses_user_pay_point",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_cashier_pay_point_accesses_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_cashier_pay_point_accesses_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cashier_pay_point_id"],
            ["cashier_pay_points.id"],
            name="fk_cashier_pay_point_accesses_pay_point",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_cashier_pay_point_accesses_user_active",
        "cashier_pay_point_accesses",
        ["user_id", "is_active", "is_default"],
    )


def _alter_billing_items(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, "billing_items"):
        return

    if not _column_exists(inspector, "billing_items", "cashier_pay_point_id"):
        with op.batch_alter_table("billing_items") as batch:
            batch.add_column(sa.Column("cashier_pay_point_id", sa.Uuid(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    if not _fk_exists(inspector, "billing_items", "fk_billing_items_cashier_pay_point"):
        with op.batch_alter_table("billing_items") as batch:
            batch.create_foreign_key(
                "fk_billing_items_cashier_pay_point",
                "cashier_pay_points",
                ["cashier_pay_point_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(op.get_bind())
    if not _index_exists(inspector, "billing_items", "ix_billing_items_cashier_pay_point_id"):
        op.create_index(
            "ix_billing_items_cashier_pay_point_id",
            "billing_items",
            ["cashier_pay_point_id"],
        )


def _alter_payment_receipts(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, "payment_receipts"):
        return

    if not _column_exists(inspector, "payment_receipts", "cashier_pay_point_id"):
        with op.batch_alter_table("payment_receipts") as batch:
            batch.add_column(sa.Column("cashier_pay_point_id", sa.Uuid(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    if not _fk_exists(inspector, "payment_receipts", "fk_payment_receipts_cashier_pay_point"):
        with op.batch_alter_table("payment_receipts") as batch:
            batch.create_foreign_key(
                "fk_payment_receipts_cashier_pay_point",
                "cashier_pay_points",
                ["cashier_pay_point_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(op.get_bind())
    if not _index_exists(inspector, "payment_receipts", "ix_payment_receipts_cashier_pay_point_id"):
        op.create_index(
            "ix_payment_receipts_cashier_pay_point_id",
            "payment_receipts",
            ["cashier_pay_point_id"],
        )


def _alter_prescriptions(inspector: sa.Inspector, *, workflow_status_enum, exception_enum) -> None:
    if not _table_exists(inspector, "prescriptions"):
        return

    with op.batch_alter_table("prescriptions") as batch:
        if not _column_exists(inspector, "prescriptions", "billing_item_id"):
            batch.add_column(sa.Column("billing_item_id", sa.Uuid(), nullable=True))
        if not _column_exists(inspector, "prescriptions", "assigned_dispensing_unit_id"):
            batch.add_column(sa.Column("assigned_dispensing_unit_id", sa.Uuid(), nullable=True))
        if not _column_exists(inspector, "prescriptions", "assigned_cashier_pay_point_id"):
            batch.add_column(sa.Column("assigned_cashier_pay_point_id", sa.Uuid(), nullable=True))
        if not _column_exists(inspector, "prescriptions", "workflow_status"):
            batch.add_column(
                sa.Column(
                    "workflow_status",
                    workflow_status_enum,
                    nullable=False,
                    server_default=PharmacyPrescriptionWorkflowStatus.ASSIGNED.value,
                )
            )
        if not _column_exists(inspector, "prescriptions", "exception_authorization_type"):
            batch.add_column(
                sa.Column(
                    "exception_authorization_type",
                    exception_enum,
                    nullable=False,
                    server_default=PharmacyExceptionAuthorizationType.NONE.value,
                )
            )
        if not _column_exists(inspector, "prescriptions", "exception_authorized_by"):
            batch.add_column(sa.Column("exception_authorized_by", sa.Uuid(), nullable=True))
        if not _column_exists(inspector, "prescriptions", "exception_authorized_at"):
            batch.add_column(sa.Column("exception_authorized_at", sa.DateTime(timezone=True), nullable=True))
        if not _column_exists(inspector, "prescriptions", "externally_fulfilled_at"):
            batch.add_column(sa.Column("externally_fulfilled_at", sa.DateTime(timezone=True), nullable=True))

    inspector = sa.inspect(op.get_bind())
    with op.batch_alter_table("prescriptions") as batch:
        if not _fk_exists(inspector, "prescriptions", "fk_prescriptions_billing_item_id"):
            batch.create_foreign_key(
                "fk_prescriptions_billing_item_id",
                "billing_items",
                ["billing_item_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _fk_exists(inspector, "prescriptions", "fk_prescriptions_assigned_dispensing_unit"):
            batch.create_foreign_key(
                "fk_prescriptions_assigned_dispensing_unit",
                "service_lines",
                ["assigned_dispensing_unit_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _fk_exists(inspector, "prescriptions", "fk_prescriptions_assigned_cashier_pay_point"):
            batch.create_foreign_key(
                "fk_prescriptions_assigned_cashier_pay_point",
                "cashier_pay_points",
                ["assigned_cashier_pay_point_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _fk_exists(inspector, "prescriptions", "fk_prescriptions_exception_authorized_by"):
            batch.create_foreign_key(
                "fk_prescriptions_exception_authorized_by",
                "users",
                ["exception_authorized_by"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(op.get_bind())
    if not _index_exists(inspector, "prescriptions", "ix_prescriptions_assigned_unit_workflow"):
        op.create_index(
            "ix_prescriptions_assigned_unit_workflow",
            "prescriptions",
            ["assigned_dispensing_unit_id", "workflow_status"],
        )


def _create_pharmacy_unit_profiles(inspector: sa.Inspector, *, unit_category_enum) -> None:
    if _table_exists(inspector, "pharmacy_unit_profiles"):
        return

    visit_service_line_enum = _existing_enum_type(
        op.get_bind(),
        name="visit_service_line",
        values=["OPD", "ANC", "MATERNITY"],
    )

    op.create_table(
        "pharmacy_unit_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("service_line_id", sa.Uuid(), nullable=False),
        sa.Column("unit_category", unit_category_enum, nullable=False),
        sa.Column("scheme_type", sa.String(length=80), nullable=True),
        sa.Column("linked_visit_service_line", visit_service_line_enum, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_pharmacy_unit_profiles_id_clinic"),
        sa.UniqueConstraint("service_line_id", name="uq_pharmacy_unit_profiles_service_line"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_unit_profiles_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_unit_profiles_service_line",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_pharmacy_unit_profiles_clinic_category",
        "pharmacy_unit_profiles",
        ["clinic_id", "unit_category"],
    )


def _create_pharmacy_user_unit_accesses(inspector: sa.Inspector) -> None:
    if _table_exists(inspector, "pharmacy_user_unit_accesses"):
        return

    op.create_table(
        "pharmacy_user_unit_accesses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("service_line_id", sa.Uuid(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "id",
            "clinic_id",
            name="uq_pharmacy_user_unit_accesses_id_clinic",
        ),
        sa.UniqueConstraint(
            "user_id",
            "service_line_id",
            name="uq_pharmacy_user_unit_accesses_user_service_line",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_user_unit_accesses_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_pharmacy_user_unit_accesses_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_user_unit_accesses_service_line",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_pharmacy_user_unit_accesses_user_active",
        "pharmacy_user_unit_accesses",
        ["user_id", "is_active", "is_default"],
    )


def _create_pharmacy_routing_rules(inspector: sa.Inspector) -> None:
    if _table_exists(inspector, "pharmacy_routing_rules"):
        return

    visit_service_line_enum = _existing_enum_type(
        op.get_bind(),
        name="visit_service_line",
        values=["OPD", "ANC", "MATERNITY"],
    )

    op.create_table(
        "pharmacy_routing_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("visit_service_line", visit_service_line_enum, nullable=True),
        sa.Column("visit_service_line_id", sa.Uuid(), nullable=True),
        sa.Column("scheme_type", sa.String(length=80), nullable=True),
        sa.Column("min_age_years", sa.Integer(), nullable=True),
        sa.Column("max_age_years", sa.Integer(), nullable=True),
        sa.Column("dispensing_unit_id", sa.Uuid(), nullable=False),
        sa.Column("cashier_pay_point_id", sa.Uuid(), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_pharmacy_routing_rules_id_clinic"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_routing_rules_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_routing_rules_visit_service_line",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["dispensing_unit_id"],
            ["service_lines.id"],
            name="fk_pharmacy_routing_rules_dispensing_unit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cashier_pay_point_id"],
            ["cashier_pay_points.id"],
            name="fk_pharmacy_routing_rules_pay_point",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_pharmacy_routing_rules_clinic_active_priority",
        "pharmacy_routing_rules",
        ["clinic_id", "is_active", "is_fallback", "priority"],
    )


def _create_refill_and_voucher_tables(
    inspector: sa.Inspector,
    *,
    refill_status_enum,
    issue_voucher_status_enum,
) -> None:
    if not _table_exists(inspector, "pharmacy_refill_requests"):
        op.create_table(
            "pharmacy_refill_requests",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("requesting_unit_id", sa.Uuid(), nullable=False),
            sa.Column("requested_by", sa.Uuid(), nullable=False),
            sa.Column(
                "status",
                refill_status_enum,
                nullable=False,
                server_default=PharmacyRefillRequestStatus.PENDING.value,
            ),
            sa.Column("urgency", sa.String(length=40), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("reviewed_by", sa.Uuid(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column(
                "requested_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "id",
                "clinic_id",
                name="uq_pharmacy_refill_requests_id_clinic",
            ),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_pharmacy_refill_requests_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["requesting_unit_id"],
                ["service_lines.id"],
                name="fk_pharmacy_refill_requests_requesting_unit",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["requested_by"],
                ["users.id"],
                name="fk_pharmacy_refill_requests_requested_by",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["reviewed_by"],
                ["users.id"],
                name="fk_pharmacy_refill_requests_reviewed_by",
                ondelete="SET NULL",
            ),
        )
        op.create_index(
            "ix_pharmacy_refill_requests_clinic_status_requested",
            "pharmacy_refill_requests",
            ["clinic_id", "status", "requested_at"],
        )

    inspector = sa.inspect(op.get_bind())
    if not _table_exists(inspector, "pharmacy_refill_request_items"):
        op.create_table(
            "pharmacy_refill_request_items",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("refill_request_id", sa.Uuid(), nullable=False),
            sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
            sa.Column("requested_quantity", sa.Integer(), nullable=False),
            sa.Column("approved_quantity", sa.Integer(), nullable=True),
            sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("issued_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("received_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "id",
                "clinic_id",
                name="uq_pharmacy_refill_request_items_id_clinic",
            ),
            sa.UniqueConstraint(
                "refill_request_id",
                "inventory_item_id",
                name="uq_pharmacy_refill_request_items_request_item",
            ),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_pharmacy_refill_request_items_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["refill_request_id"],
                ["pharmacy_refill_requests.id"],
                name="fk_pharmacy_refill_request_items_request",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["inventory_item_id"],
                ["pharmacy_inventory_items.id"],
                name="fk_pharmacy_refill_request_items_inventory_item",
                ondelete="RESTRICT",
            ),
            sa.CheckConstraint(
                "requested_quantity > 0",
                name="ck_pharmacy_refill_request_items_requested_positive",
            ),
            sa.CheckConstraint(
                "(approved_quantity IS NULL) OR (approved_quantity >= 0)",
                name="ck_pharmacy_refill_request_items_approved_non_negative",
            ),
            sa.CheckConstraint(
                "reserved_quantity >= 0 AND issued_quantity >= 0 AND received_quantity >= 0",
                name="ck_pharmacy_refill_request_items_progress_non_negative",
            ),
        )

    inspector = sa.inspect(op.get_bind())
    if not _table_exists(inspector, "pharmacy_issue_vouchers"):
        op.create_table(
            "pharmacy_issue_vouchers",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("voucher_number", sa.String(length=64), nullable=False),
            sa.Column("store_unit_id", sa.Uuid(), nullable=False),
            sa.Column("receiving_unit_id", sa.Uuid(), nullable=False),
            sa.Column("refill_request_id", sa.Uuid(), nullable=True),
            sa.Column(
                "status",
                issue_voucher_status_enum,
                nullable=False,
                server_default=PharmacyIssueVoucherStatus.ISSUED.value,
            ),
            sa.Column("prepared_by", sa.Uuid(), nullable=True),
            sa.Column("approved_by", sa.Uuid(), nullable=True),
            sa.Column("issued_by", sa.Uuid(), nullable=False),
            sa.Column(
                "issued_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "id",
                "clinic_id",
                name="uq_pharmacy_issue_vouchers_id_clinic",
            ),
            sa.UniqueConstraint(
                "clinic_id",
                "voucher_number",
                name="uq_pharmacy_issue_vouchers_clinic_number",
            ),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_pharmacy_issue_vouchers_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["store_unit_id"],
                ["service_lines.id"],
                name="fk_pharmacy_issue_vouchers_store_unit",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["receiving_unit_id"],
                ["service_lines.id"],
                name="fk_pharmacy_issue_vouchers_receiving_unit",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["refill_request_id"],
                ["pharmacy_refill_requests.id"],
                name="fk_pharmacy_issue_vouchers_refill_request",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["prepared_by"],
                ["users.id"],
                name="fk_pharmacy_issue_vouchers_prepared_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["approved_by"],
                ["users.id"],
                name="fk_pharmacy_issue_vouchers_approved_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["issued_by"],
                ["users.id"],
                name="fk_pharmacy_issue_vouchers_issued_by",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["acknowledged_by"],
                ["users.id"],
                name="fk_pharmacy_issue_vouchers_acknowledged_by",
                ondelete="SET NULL",
            ),
        )
        op.create_index(
            "ix_pharmacy_issue_vouchers_clinic_status_issued_at",
            "pharmacy_issue_vouchers",
            ["clinic_id", "status", "issued_at"],
        )

    inspector = sa.inspect(op.get_bind())
    if not _table_exists(inspector, "pharmacy_issue_voucher_items"):
        op.create_table(
            "pharmacy_issue_voucher_items",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("voucher_id", sa.Uuid(), nullable=False),
            sa.Column("refill_request_item_id", sa.Uuid(), nullable=True),
            sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
            sa.Column("batch_number", sa.String(length=80), nullable=False),
            sa.Column("expiry_date", sa.Date(), nullable=True),
            sa.Column("issued_quantity", sa.Integer(), nullable=False),
            sa.Column("received_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "id",
                "clinic_id",
                name="uq_pharmacy_issue_voucher_items_id_clinic",
            ),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_pharmacy_issue_voucher_items_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["voucher_id"],
                ["pharmacy_issue_vouchers.id"],
                name="fk_pharmacy_issue_voucher_items_voucher",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["refill_request_item_id"],
                ["pharmacy_refill_request_items.id"],
                name="fk_pharmacy_issue_voucher_items_request_item",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["inventory_item_id"],
                ["pharmacy_inventory_items.id"],
                name="fk_pharmacy_issue_voucher_items_inventory_item",
                ondelete="RESTRICT",
            ),
            sa.CheckConstraint(
                "issued_quantity > 0",
                name="ck_pharmacy_issue_voucher_items_issued_positive",
            ),
            sa.CheckConstraint(
                "received_quantity >= 0 AND received_quantity <= issued_quantity",
                name="ck_pharmacy_issue_voucher_items_received_range",
            ),
        )


def _create_pharmacy_unit_stock_lots(inspector: sa.Inspector) -> None:
    if _table_exists(inspector, "pharmacy_unit_stock_lots"):
        return

    op.create_table(
        "pharmacy_unit_stock_lots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("service_line_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("batch_number", sa.String(length=80), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "id",
            "clinic_id",
            name="uq_pharmacy_unit_stock_lots_id_clinic",
        ),
        sa.UniqueConstraint(
            "service_line_id",
            "inventory_item_id",
            "batch_number",
            "expiry_date",
            name="uq_pharmacy_unit_stock_lots_unit_item_batch",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_unit_stock_lots_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_line_id"],
            ["service_lines.id"],
            name="fk_pharmacy_unit_stock_lots_service_line",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pharmacy_inventory_items.id"],
            name="fk_pharmacy_unit_stock_lots_inventory_item",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "quantity_on_hand >= 0",
            name="ck_pharmacy_unit_stock_lots_quantity_non_negative",
        ),
    )
    op.create_index(
        "ix_pharmacy_unit_stock_lots_unit_item",
        "pharmacy_unit_stock_lots",
        ["service_line_id", "inventory_item_id"],
    )


def _alter_pharmacy_stock_movements(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, "pharmacy_stock_movements"):
        return

    if not _column_exists(inspector, "pharmacy_stock_movements", "service_line_id"):
        with op.batch_alter_table("pharmacy_stock_movements") as batch:
            batch.add_column(sa.Column("service_line_id", sa.Uuid(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    with op.batch_alter_table("pharmacy_stock_movements") as batch:
        if not _fk_exists(inspector, "pharmacy_stock_movements", "fk_pharmacy_stock_movements_service_line"):
            batch.create_foreign_key(
                "fk_pharmacy_stock_movements_service_line",
                "service_lines",
                ["service_line_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(op.get_bind())
    with op.batch_alter_table("pharmacy_stock_movements") as batch:
        if _check_exists(inspector, "pharmacy_stock_movements", "ck_pharmacy_stock_movements_type"):
            batch.drop_constraint("ck_pharmacy_stock_movements_type", type_="check")
        batch.create_check_constraint(
            "ck_pharmacy_stock_movements_type",
            "movement_type IN ('RESTOCK','DISPENSE','ISSUE','RECEIVE','RETURN','ADJUSTMENT','PRICE_UPDATE','ACTIVATED','INACTIVATED')",
        )


def _seed_existing_clinics(bind) -> None:
    from app.services.pharmacy_seed_service import PharmacySeedService

    session = Session(bind=bind)
    try:
        clinic_ids = [row.id for row in session.execute(sa.text("SELECT id FROM clinics")).all()]
        seed_service = PharmacySeedService(session)
        for clinic_id in clinic_ids:
            seed_service.seed_kazaure_structure(clinic_id=clinic_id, commit=False)
        session.commit()
    finally:
        session.close()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    workflow_status_enum = _enum_type(
        bind,
        name="pharmacy_prescription_workflow_status",
        values=_enum_values(PharmacyPrescriptionWorkflowStatus),
    )
    exception_enum = _enum_type(
        bind,
        name="pharmacy_exception_authorization_type",
        values=_enum_values(PharmacyExceptionAuthorizationType),
    )
    unit_category_enum = _enum_type(
        bind,
        name="pharmacy_unit_category",
        values=_enum_values(PharmacyUnitCategory),
    )
    refill_status_enum = _enum_type(
        bind,
        name="pharmacy_refill_request_status",
        values=_enum_values(PharmacyRefillRequestStatus),
    )
    issue_voucher_status_enum = _enum_type(
        bind,
        name="pharmacy_issue_voucher_status",
        values=_enum_values(PharmacyIssueVoucherStatus),
    )

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            bind.execute(
                sa.text(
                    "ALTER TYPE service_line_kind ADD VALUE IF NOT EXISTS 'PHARMACY_UNIT'"
                )
            )
            bind.execute(
                sa.text(
                    "ALTER TYPE prescription_status ADD VALUE IF NOT EXISTS 'EXTERNALLY_FULFILLED'"
                )
            )

    _create_cashier_pay_points(inspector)
    inspector = sa.inspect(bind)
    _create_cashier_pay_point_accesses(inspector)
    inspector = sa.inspect(bind)
    _alter_billing_items(inspector)
    inspector = sa.inspect(bind)
    _alter_payment_receipts(inspector)
    inspector = sa.inspect(bind)
    _alter_prescriptions(
        inspector,
        workflow_status_enum=workflow_status_enum,
        exception_enum=exception_enum,
    )
    inspector = sa.inspect(bind)
    _create_pharmacy_unit_profiles(inspector, unit_category_enum=unit_category_enum)
    inspector = sa.inspect(bind)
    _create_pharmacy_user_unit_accesses(inspector)
    inspector = sa.inspect(bind)
    _create_pharmacy_routing_rules(inspector)
    inspector = sa.inspect(bind)
    _create_refill_and_voucher_tables(
        inspector,
        refill_status_enum=refill_status_enum,
        issue_voucher_status_enum=issue_voucher_status_enum,
    )
    inspector = sa.inspect(bind)
    _create_pharmacy_unit_stock_lots(inspector)
    inspector = sa.inspect(bind)
    _alter_pharmacy_stock_movements(inspector)
    _seed_existing_clinics(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "pharmacy_stock_movements"):
        with op.batch_alter_table("pharmacy_stock_movements") as batch:
            if _check_exists(inspector, "pharmacy_stock_movements", "ck_pharmacy_stock_movements_type"):
                batch.drop_constraint("ck_pharmacy_stock_movements_type", type_="check")
            batch.create_check_constraint(
                "ck_pharmacy_stock_movements_type",
                "movement_type IN ('RESTOCK','DISPENSE','ADJUSTMENT','PRICE_UPDATE','ACTIVATED','INACTIVATED')",
            )
            if _fk_exists(inspector, "pharmacy_stock_movements", "fk_pharmacy_stock_movements_service_line"):
                batch.drop_constraint("fk_pharmacy_stock_movements_service_line", type_="foreignkey")
            if _column_exists(inspector, "pharmacy_stock_movements", "service_line_id"):
                batch.drop_column("service_line_id")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "pharmacy_unit_stock_lots"):
        if _index_exists(inspector, "pharmacy_unit_stock_lots", "ix_pharmacy_unit_stock_lots_unit_item"):
            op.drop_index("ix_pharmacy_unit_stock_lots_unit_item", table_name="pharmacy_unit_stock_lots")
        op.drop_table("pharmacy_unit_stock_lots")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "pharmacy_issue_voucher_items"):
        op.drop_table("pharmacy_issue_voucher_items")
    if _table_exists(inspector, "pharmacy_issue_vouchers"):
        if _index_exists(inspector, "pharmacy_issue_vouchers", "ix_pharmacy_issue_vouchers_clinic_status_issued_at"):
            op.drop_index(
                "ix_pharmacy_issue_vouchers_clinic_status_issued_at",
                table_name="pharmacy_issue_vouchers",
            )
        op.drop_table("pharmacy_issue_vouchers")
    if _table_exists(inspector, "pharmacy_refill_request_items"):
        op.drop_table("pharmacy_refill_request_items")
    if _table_exists(inspector, "pharmacy_refill_requests"):
        if _index_exists(inspector, "pharmacy_refill_requests", "ix_pharmacy_refill_requests_clinic_status_requested"):
            op.drop_index(
                "ix_pharmacy_refill_requests_clinic_status_requested",
                table_name="pharmacy_refill_requests",
            )
        op.drop_table("pharmacy_refill_requests")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "pharmacy_routing_rules"):
        if _index_exists(inspector, "pharmacy_routing_rules", "ix_pharmacy_routing_rules_clinic_active_priority"):
            op.drop_index(
                "ix_pharmacy_routing_rules_clinic_active_priority",
                table_name="pharmacy_routing_rules",
            )
        op.drop_table("pharmacy_routing_rules")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "pharmacy_user_unit_accesses"):
        if _index_exists(inspector, "pharmacy_user_unit_accesses", "ix_pharmacy_user_unit_accesses_user_active"):
            op.drop_index(
                "ix_pharmacy_user_unit_accesses_user_active",
                table_name="pharmacy_user_unit_accesses",
            )
        op.drop_table("pharmacy_user_unit_accesses")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "pharmacy_unit_profiles"):
        if _index_exists(inspector, "pharmacy_unit_profiles", "ix_pharmacy_unit_profiles_clinic_category"):
            op.drop_index(
                "ix_pharmacy_unit_profiles_clinic_category",
                table_name="pharmacy_unit_profiles",
            )
        op.drop_table("pharmacy_unit_profiles")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "prescriptions"):
        with op.batch_alter_table("prescriptions") as batch:
            if _index_exists(inspector, "prescriptions", "ix_prescriptions_assigned_unit_workflow"):
                op.drop_index(
                    "ix_prescriptions_assigned_unit_workflow",
                    table_name="prescriptions",
                )
            if _fk_exists(inspector, "prescriptions", "fk_prescriptions_exception_authorized_by"):
                batch.drop_constraint("fk_prescriptions_exception_authorized_by", type_="foreignkey")
            if _fk_exists(inspector, "prescriptions", "fk_prescriptions_assigned_cashier_pay_point"):
                batch.drop_constraint("fk_prescriptions_assigned_cashier_pay_point", type_="foreignkey")
            if _fk_exists(inspector, "prescriptions", "fk_prescriptions_assigned_dispensing_unit"):
                batch.drop_constraint("fk_prescriptions_assigned_dispensing_unit", type_="foreignkey")
            if _fk_exists(inspector, "prescriptions", "fk_prescriptions_billing_item_id"):
                batch.drop_constraint("fk_prescriptions_billing_item_id", type_="foreignkey")
            for column in (
                "externally_fulfilled_at",
                "exception_authorized_at",
                "exception_authorized_by",
                "exception_authorization_type",
                "workflow_status",
                "assigned_cashier_pay_point_id",
                "assigned_dispensing_unit_id",
                "billing_item_id",
            ):
                if _column_exists(inspector, "prescriptions", column):
                    batch.drop_column(column)

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "payment_receipts"):
        with op.batch_alter_table("payment_receipts") as batch:
            if _fk_exists(inspector, "payment_receipts", "fk_payment_receipts_cashier_pay_point"):
                batch.drop_constraint("fk_payment_receipts_cashier_pay_point", type_="foreignkey")
            if _column_exists(inspector, "payment_receipts", "cashier_pay_point_id"):
                batch.drop_column("cashier_pay_point_id")
        if _index_exists(inspector, "payment_receipts", "ix_payment_receipts_cashier_pay_point_id"):
            op.drop_index(
                "ix_payment_receipts_cashier_pay_point_id",
                table_name="payment_receipts",
            )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "billing_items"):
        with op.batch_alter_table("billing_items") as batch:
            if _fk_exists(inspector, "billing_items", "fk_billing_items_cashier_pay_point"):
                batch.drop_constraint("fk_billing_items_cashier_pay_point", type_="foreignkey")
            if _column_exists(inspector, "billing_items", "cashier_pay_point_id"):
                batch.drop_column("cashier_pay_point_id")
        if _index_exists(inspector, "billing_items", "ix_billing_items_cashier_pay_point_id"):
            op.drop_index(
                "ix_billing_items_cashier_pay_point_id",
                table_name="billing_items",
            )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "cashier_pay_point_accesses"):
        if _index_exists(inspector, "cashier_pay_point_accesses", "ix_cashier_pay_point_accesses_user_active"):
            op.drop_index(
                "ix_cashier_pay_point_accesses_user_active",
                table_name="cashier_pay_point_accesses",
            )
        op.drop_table("cashier_pay_point_accesses")
    if _table_exists(inspector, "cashier_pay_points"):
        if _index_exists(inspector, "cashier_pay_points", "ix_cashier_pay_points_clinic_active_name"):
            op.drop_index(
                "ix_cashier_pay_points_clinic_active_name",
                table_name="cashier_pay_points",
            )
        op.drop_table("cashier_pay_points")

    if bind.dialect.name == "postgresql":
        for enum_name in (
            "pharmacy_issue_voucher_status",
            "pharmacy_refill_request_status",
            "pharmacy_unit_category",
            "pharmacy_exception_authorization_type",
            "pharmacy_prescription_workflow_status",
        ):
            bind.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
