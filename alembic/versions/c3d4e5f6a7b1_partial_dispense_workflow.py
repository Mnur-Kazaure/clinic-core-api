"""partial dispense workflow

Revision ID: c3d4e5f6a7b1
Revises: b2c3d4e5f6a
Create Date: 2026-03-26 17:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b1"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_check_constraint(
    inspector: sa.Inspector, table_name: str, constraint_name: str
) -> bool:
    return constraint_name in {
        row["name"] for row in inspector.get_check_constraints(table_name)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            bind.execute(
                sa.text(
                    "ALTER TYPE pharmacy_prescription_workflow_status "
                    "ADD VALUE IF NOT EXISTS 'PARTIALLY_DISPENSED'"
                )
            )

    if not _has_column(inspector, "prescriptions", "quantity_prescribed"):
        op.add_column(
            "prescriptions",
            sa.Column(
                "quantity_prescribed",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )
    if not _has_column(inspector, "prescriptions", "quantity_dispensed_total"):
        op.add_column(
            "prescriptions",
            sa.Column(
                "quantity_dispensed_total",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if not _has_column(inspector, "prescriptions", "quantity_remaining"):
        op.add_column(
            "prescriptions",
            sa.Column(
                "quantity_remaining",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )

    bind.execute(
        sa.text(
            """
            UPDATE prescriptions
            SET quantity_prescribed = COALESCE(NULLIF(quantity_prescribed, 0), 1)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE prescriptions
            SET quantity_dispensed_total = CASE
                WHEN status = 'DISPENSED' THEN GREATEST(COALESCE(quantity_dispensed_total, 0), quantity_prescribed)
                ELSE COALESCE(quantity_dispensed_total, 0)
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE prescriptions
            SET quantity_remaining = CASE
                WHEN status IN ('DISPENSED', 'CANCELLED', 'EXTERNALLY_FULFILLED') THEN 0
                ELSE GREATEST(quantity_prescribed - COALESCE(quantity_dispensed_total, 0), 0)
            END
            """
        )
    )

    inspector = sa.inspect(bind)
    if not _has_check_constraint(
        inspector,
        "prescriptions",
        "ck_prescription_quantity_prescribed_positive",
    ):
        op.create_check_constraint(
            "ck_prescription_quantity_prescribed_positive",
            "prescriptions",
            "quantity_prescribed > 0",
        )
    if not _has_check_constraint(
        inspector,
        "prescriptions",
        "ck_prescription_quantity_dispensed_total_non_negative",
    ):
        op.create_check_constraint(
            "ck_prescription_quantity_dispensed_total_non_negative",
            "prescriptions",
            "quantity_dispensed_total >= 0",
        )
    if not _has_check_constraint(
        inspector,
        "prescriptions",
        "ck_prescription_quantity_remaining_non_negative",
    ):
        op.create_check_constraint(
            "ck_prescription_quantity_remaining_non_negative",
            "prescriptions",
            "quantity_remaining >= 0",
        )
    if not _has_check_constraint(
        inspector,
        "prescriptions",
        "ck_prescription_quantity_dispensed_total_lte_prescribed",
    ):
        op.create_check_constraint(
            "ck_prescription_quantity_dispensed_total_lte_prescribed",
            "prescriptions",
            "quantity_dispensed_total <= quantity_prescribed",
        )
    if not _has_check_constraint(
        inspector,
        "prescriptions",
        "ck_prescription_quantity_remaining_lte_prescribed",
    ):
        op.create_check_constraint(
            "ck_prescription_quantity_remaining_lte_prescribed",
            "prescriptions",
            "quantity_remaining <= quantity_prescribed",
        )

    if not _has_column(inspector, "dispensations", "stock_lot_id"):
        op.add_column(
            "dispensations",
            sa.Column("stock_lot_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            "fk_dispensations_stock_lot_id",
            "dispensations",
            "pharmacy_unit_stock_lots",
            ["stock_lot_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if not _has_column(inspector, "dispensations", "batch_number"):
        op.add_column(
            "dispensations",
            sa.Column("batch_number", sa.String(length=100), nullable=True),
        )
    if not _has_column(inspector, "dispensations", "expiry_date"):
        op.add_column(
            "dispensations",
            sa.Column("expiry_date", sa.Date(), nullable=True),
        )
    if not _has_column(inspector, "dispensations", "dispensing_unit_id"):
        op.add_column(
            "dispensations",
            sa.Column("dispensing_unit_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            "fk_dispensations_dispensing_unit_id",
            "dispensations",
            "service_lines",
            ["dispensing_unit_id"],
            ["id"],
            ondelete="SET NULL",
        )

    bind.execute(
        sa.text(
            """
            UPDATE dispensations AS d
            SET dispensing_unit_id = p.assigned_dispensing_unit_id
            FROM prescriptions AS p
            WHERE d.prescription_id = p.id
              AND d.dispensing_unit_id IS NULL
            """
        )
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prescriptions_block_update_signed()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.record_status = 'VOIDED' THEN
                RAISE EXCEPTION 'signed record immutable';
            END IF;

            IF OLD.record_status = 'SIGNED' THEN
                IF NEW.record_status NOT IN ('SIGNED', 'VOIDED') THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;

                IF NEW.record_status = 'VOIDED' AND (
                    NEW.void_reason IS NULL OR
                    NEW.status <> 'CANCELLED' OR
                    NEW.cancelled_at IS NULL
                ) THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;

                IF
                    NEW.consultation_id IS DISTINCT FROM OLD.consultation_id OR
                    NEW.visit_id IS DISTINCT FROM OLD.visit_id OR
                    NEW.clinic_id IS DISTINCT FROM OLD.clinic_id OR
                    NEW.prescribed_by IS DISTINCT FROM OLD.prescribed_by OR
                    NEW.drug_name IS DISTINCT FROM OLD.drug_name OR
                    NEW.dosage IS DISTINCT FROM OLD.dosage OR
                    NEW.frequency IS DISTINCT FROM OLD.frequency OR
                    NEW.duration IS DISTINCT FROM OLD.duration OR
                    NEW.instructions IS DISTINCT FROM OLD.instructions OR
                    NEW.quantity_prescribed IS DISTINCT FROM OLD.quantity_prescribed OR
                    NEW.issued_at IS DISTINCT FROM OLD.issued_at OR
                    NEW.signed_at IS DISTINCT FROM OLD.signed_at
                THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prescriptions_block_update_signed()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.record_status = 'VOIDED' THEN
                RAISE EXCEPTION 'signed record immutable';
            END IF;

            IF OLD.record_status = 'SIGNED' THEN
                IF NEW.record_status NOT IN ('SIGNED', 'VOIDED') THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;

                IF NEW.record_status = 'VOIDED' AND (
                    NEW.void_reason IS NULL OR
                    NEW.status <> 'CANCELLED' OR
                    NEW.cancelled_at IS NULL
                ) THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;

                IF
                    NEW.consultation_id IS DISTINCT FROM OLD.consultation_id OR
                    NEW.visit_id IS DISTINCT FROM OLD.visit_id OR
                    NEW.clinic_id IS DISTINCT FROM OLD.clinic_id OR
                    NEW.prescribed_by IS DISTINCT FROM OLD.prescribed_by OR
                    NEW.drug_name IS DISTINCT FROM OLD.drug_name OR
                    NEW.dosage IS DISTINCT FROM OLD.dosage OR
                    NEW.frequency IS DISTINCT FROM OLD.frequency OR
                    NEW.duration IS DISTINCT FROM OLD.duration OR
                    NEW.instructions IS DISTINCT FROM OLD.instructions OR
                    NEW.issued_at IS DISTINCT FROM OLD.issued_at OR
                    NEW.signed_at IS DISTINCT FROM OLD.signed_at
                THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    with op.batch_alter_table("dispensations") as batch_op:
        batch_op.drop_constraint("fk_dispensations_dispensing_unit_id", type_="foreignkey")
        batch_op.drop_column("dispensing_unit_id")
        batch_op.drop_column("expiry_date")
        batch_op.drop_column("batch_number")
        batch_op.drop_constraint("fk_dispensations_stock_lot_id", type_="foreignkey")
        batch_op.drop_column("stock_lot_id")

    with op.batch_alter_table("prescriptions") as batch_op:
        batch_op.drop_constraint(
            "ck_prescription_quantity_remaining_lte_prescribed", type_="check"
        )
        batch_op.drop_constraint(
            "ck_prescription_quantity_dispensed_total_lte_prescribed", type_="check"
        )
        batch_op.drop_constraint(
            "ck_prescription_quantity_remaining_non_negative", type_="check"
        )
        batch_op.drop_constraint(
            "ck_prescription_quantity_dispensed_total_non_negative", type_="check"
        )
        batch_op.drop_constraint(
            "ck_prescription_quantity_prescribed_positive", type_="check"
        )
        batch_op.drop_column("quantity_remaining")
        batch_op.drop_column("quantity_dispensed_total")
        batch_op.drop_column("quantity_prescribed")
