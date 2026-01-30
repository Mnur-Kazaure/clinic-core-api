"""clean_install_fixup

Revision ID: 765723687708
Revises: c1d2e3f4g5h6
Create Date: 2026-01-28 11:22:37.479617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '765723687708'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def table_exists(name: str) -> bool:
        if conn.dialect.name == "postgresql":
            return (
                conn.execute(
                    sa.text("SELECT to_regclass(:name)"),
                    {"name": f"public.{name}"},
                ).scalar()
                is not None
            )
        return name in inspector.get_table_names()

    def column_exists(table: str, column: str) -> bool:
        if conn.dialect.name == "postgresql":
            return (
                conn.execute(
                    sa.text(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                          AND column_name = :column_name
                        """
                    ),
                    {"table_name": table, "column_name": column},
                ).scalar()
                is not None
            )
        return column in {col["name"] for col in inspector.get_columns(table)}

    def check_constraint_exists(table: str, name: str) -> bool:
        return name in {ck["name"] for ck in inspector.get_check_constraints(table)}

    def unique_exists(table: str, name: str) -> bool:
        return name in {uq["name"] for uq in inspector.get_unique_constraints(table)}

    def unique_matches(table: str, columns: list[str]) -> bool:
        for uq in inspector.get_unique_constraints(table):
            if uq.get("column_names") == columns:
                return True
        return False

    def fk_matches(table: str, columns: list[str], ref_table: str, ref_columns: list[str]) -> bool:
        for fk in inspector.get_foreign_keys(table):
            if (
                fk.get("referred_table") == ref_table
                and fk.get("constrained_columns") == columns
                and fk.get("referred_columns") == ref_columns
            ):
                return True
        return False

    default_now = sa.text("CURRENT_TIMESTAMP") if conn.dialect.name == "sqlite" else sa.text("now()")

    if conn.dialect.name == "postgresql":
        from sqlalchemy.dialects import postgresql

        record_status_enum = postgresql.ENUM(
            "DRAFT",
            "SIGNED",
            "AMENDED",
            "VOIDED",
            name="record_status",
            create_type=False,
        )
        record_status_enum.create(conn, checkfirst=True)

        prescription_status_enum = postgresql.ENUM(
            "ISSUED",
            "DISPENSED",
            "CANCELLED",
            name="prescription_status",
            create_type=False,
        )
        prescription_status_enum.create(conn, checkfirst=True)
    else:
        record_status_enum = sa.Enum(
            "DRAFT",
            "SIGNED",
            "AMENDED",
            "VOIDED",
            name="record_status",
        )
        prescription_status_enum = sa.Enum(
            "ISSUED",
            "DISPENSED",
            "CANCELLED",
            name="prescription_status",
        )

    if not table_exists("consultations"):
        op.create_table(
            "consultations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("visit_id", sa.Uuid(), nullable=False),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("doctor_id", sa.Uuid(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("record_status", record_status_enum, nullable=False, server_default="DRAFT"),
            sa.Column("void_reason", sa.Text(), nullable=True),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("vitals", sa.Text(), nullable=True),
            sa.Column("presenting_complaints", sa.Text(), nullable=True),
            sa.Column("diagnosis", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("doctor_full_name", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["visit_id", "clinic_id"],
                ["visits.id", "visits.clinic_id"],
                name="fk_consultations_visit_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["doctor_id"], ["users.id"]),
            sa.UniqueConstraint("visit_id", name="uq_consultation_visit"),
        )
    else:
        with op.batch_alter_table("consultations") as batch:
            if not column_exists("consultations", "clinic_id"):
                batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))
            if not column_exists("consultations", "record_status"):
                batch.add_column(
                    sa.Column("record_status", record_status_enum, nullable=False, server_default="DRAFT")
                )
            if not column_exists("consultations", "void_reason"):
                batch.add_column(sa.Column("void_reason", sa.Text(), nullable=True))
            if not column_exists("consultations", "signed_at"):
                batch.add_column(sa.Column("signed_at", sa.DateTime(timezone=True)))
            if not column_exists("consultations", "doctor_full_name"):
                batch.add_column(sa.Column("doctor_full_name", sa.Text(), nullable=True))
        if not check_constraint_exists("consultations", "ck_consultations_void_reason"):
            op.create_check_constraint(
                "ck_consultations_void_reason",
                "consultations",
                "(record_status != 'VOIDED') OR (void_reason IS NOT NULL)",
            )
        if not unique_exists("consultations", "uq_consultation_visit"):
            op.create_unique_constraint("uq_consultation_visit", "consultations", ["visit_id"])
        if not fk_matches(
            "consultations",
            ["visit_id", "clinic_id"],
            "visits",
            ["id", "clinic_id"],
        ):
            op.create_foreign_key(
                "fk_consultations_visit_clinic",
                "consultations",
                "visits",
                ["visit_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )

    if not table_exists("lab_results"):
        op.create_table(
            "lab_results",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("lab_request_id", sa.Uuid(), nullable=False),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("technician_id", sa.Uuid(), nullable=False),
            sa.Column("result_value", sa.String(length=255), nullable=False),
            sa.Column("result_unit", sa.String(length=50), nullable=True),
            sa.Column("reference_range", sa.String(length=100), nullable=True),
            sa.Column("record_status", record_status_enum, nullable=False, server_default="DRAFT"),
            sa.Column("void_reason", sa.String(length=255), nullable=True),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.ForeignKeyConstraint(["lab_request_id"], ["lab_requests.id"]),
            sa.ForeignKeyConstraint(
                ["lab_request_id", "clinic_id"],
                ["lab_requests.id", "lab_requests.clinic_id"],
                name="fk_lab_results_request_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["technician_id"], ["users.id"]),
        )
    else:
        with op.batch_alter_table("lab_results") as batch:
            if not column_exists("lab_results", "clinic_id"):
                batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))
            if not column_exists("lab_results", "record_status"):
                batch.add_column(
                    sa.Column("record_status", record_status_enum, nullable=False, server_default="DRAFT")
                )
            if not column_exists("lab_results", "void_reason"):
                batch.add_column(sa.Column("void_reason", sa.String(length=255), nullable=True))
            if not column_exists("lab_results", "signed_at"):
                batch.add_column(sa.Column("signed_at", sa.DateTime(timezone=True)))
        if not check_constraint_exists("lab_results", "ck_lab_results_void_reason"):
            op.create_check_constraint(
                "ck_lab_results_void_reason",
                "lab_results",
                "(record_status != 'VOIDED') OR (void_reason IS NOT NULL)",
            )
        if not fk_matches(
            "lab_results",
            ["lab_request_id", "clinic_id"],
            "lab_requests",
            ["id", "clinic_id"],
        ):
            op.create_foreign_key(
                "fk_lab_results_request_clinic",
                "lab_results",
                "lab_requests",
                ["lab_request_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )

    if not table_exists("dispensations"):
        op.create_table(
            "dispensations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("prescription_id", sa.Uuid(), nullable=False),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("pharmacist_id", sa.Uuid(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"]),
            sa.ForeignKeyConstraint(
                ["prescription_id", "clinic_id"],
                ["prescriptions.id", "prescriptions.clinic_id"],
                name="fk_dispensations_prescription_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["pharmacist_id"], ["users.id"]),
        )
    else:
        with op.batch_alter_table("dispensations") as batch:
            if not column_exists("dispensations", "clinic_id"):
                batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))
        if not fk_matches(
            "dispensations",
            ["prescription_id", "clinic_id"],
            "prescriptions",
            ["id", "clinic_id"],
        ):
            op.create_foreign_key(
                "fk_dispensations_prescription_clinic",
                "dispensations",
                "prescriptions",
                ["prescription_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )

    if not table_exists("idempotency_keys"):
        op.create_table(
            "idempotency_keys",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("endpoint", sa.String(), nullable=False),
            sa.Column("request_hash", sa.String(), nullable=False),
            sa.Column("response_body", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=default_now, nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )

    if table_exists("prescriptions"):
        with op.batch_alter_table("prescriptions") as batch:
            if not column_exists("prescriptions", "consultation_id"):
                batch.add_column(sa.Column("consultation_id", sa.Uuid(), nullable=True))
            if not column_exists("prescriptions", "dispensed_by"):
                batch.add_column(sa.Column("dispensed_by", sa.Uuid(), nullable=True))
            if not column_exists("prescriptions", "instructions"):
                batch.add_column(sa.Column("instructions", sa.String(length=500), nullable=True))
            if not column_exists("prescriptions", "status"):
                batch.add_column(
                    sa.Column(
                        "status",
                        prescription_status_enum,
                        nullable=False,
                        server_default="ISSUED",
                    )
                )
            if not column_exists("prescriptions", "issued_at"):
                batch.add_column(
                    sa.Column(
                        "issued_at",
                        sa.DateTime(timezone=True),
                        nullable=False,
                        server_default=default_now,
                    )
                )
            if not column_exists("prescriptions", "dispensed_at"):
                batch.add_column(sa.Column("dispensed_at", sa.DateTime(timezone=True), nullable=True))
            if not column_exists("prescriptions", "cancelled_at"):
                batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
            if not column_exists("prescriptions", "record_status"):
                batch.add_column(
                    sa.Column(
                        "record_status",
                        record_status_enum,
                        nullable=False,
                        server_default="DRAFT",
                    )
                )
            if not column_exists("prescriptions", "void_reason"):
                batch.add_column(sa.Column("void_reason", sa.String(length=255), nullable=True))
            if not column_exists("prescriptions", "signed_at"):
                batch.add_column(sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))

    # Ensure composite parent unique constraints exist for tenant-scoped FKs (skip on SQLite)
    if conn.dialect.name != "sqlite":
        if table_exists("visits") and not unique_matches("visits", ["id", "clinic_id"]):
            if not unique_exists("visits", "uq_visits_id_clinic"):
                op.create_unique_constraint("uq_visits_id_clinic", "visits", ["id", "clinic_id"])
        if table_exists("lab_requests") and not unique_matches("lab_requests", ["id", "clinic_id"]):
            if not unique_exists("lab_requests", "uq_lab_requests_id_clinic"):
                op.create_unique_constraint("uq_lab_requests_id_clinic", "lab_requests", ["id", "clinic_id"])
        if table_exists("prescriptions") and not unique_matches("prescriptions", ["id", "clinic_id"]):
            if not unique_exists("prescriptions", "uq_prescriptions_id_clinic"):
                op.create_unique_constraint("uq_prescriptions_id_clinic", "prescriptions", ["id", "clinic_id"])

    # Ensure immutability triggers exist for newly created tables
    if conn.dialect.name != "sqlite":
        for table in ("consultations", "prescriptions", "lab_results"):
            if table_exists(table):
                op.execute(
                    f"DROP TRIGGER IF EXISTS {table}_block_update_signed ON {table};"
                )
                op.execute(
                    f"DROP TRIGGER IF EXISTS {table}_block_delete_signed ON {table};"
                )
        if table_exists("consultations"):
            op.execute(
                """
                CREATE OR REPLACE FUNCTION consultations_block_update_signed()
                RETURNS trigger AS $$
                BEGIN
                    IF OLD.record_status = 'VOIDED' THEN
                        RAISE EXCEPTION 'signed record immutable';
                    END IF;
                    IF OLD.record_status = 'SIGNED' AND (
                        NEW.record_status <> 'VOIDED' OR NEW.void_reason IS NULL OR
                        NEW.visit_id <> OLD.visit_id OR
                        NEW.clinic_id <> OLD.clinic_id OR
                        NEW.doctor_id <> OLD.doctor_id OR
                        NEW.started_at <> OLD.started_at OR
                        NEW.completed_at <> OLD.completed_at OR
                        NEW.vitals <> OLD.vitals OR
                        NEW.presenting_complaints <> OLD.presenting_complaints OR
                        NEW.diagnosis <> OLD.diagnosis OR
                        NEW.notes <> OLD.notes OR
                        NEW.doctor_full_name <> OLD.doctor_full_name OR
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
                CREATE OR REPLACE FUNCTION consultations_block_delete_signed()
                RETURNS trigger AS $$
                BEGIN
                    IF OLD.record_status IN ('SIGNED', 'VOIDED') THEN
                        RAISE EXCEPTION 'signed record immutable';
                    END IF;
                    RETURN OLD;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
            op.execute(
                """
                CREATE TRIGGER consultations_block_update_signed
                BEFORE UPDATE ON consultations
                FOR EACH ROW
                EXECUTE FUNCTION consultations_block_update_signed();
                """
            )
            op.execute(
                """
                CREATE TRIGGER consultations_block_delete_signed
                BEFORE DELETE ON consultations
                FOR EACH ROW
                EXECUTE FUNCTION consultations_block_delete_signed();
                """
            )
        if table_exists("prescriptions"):
            op.execute(
                """
                CREATE OR REPLACE FUNCTION prescriptions_block_update_signed()
                RETURNS trigger AS $$
                BEGIN
                    IF OLD.record_status = 'VOIDED' THEN
                        RAISE EXCEPTION 'signed record immutable';
                    END IF;
                    IF OLD.record_status = 'SIGNED' AND (
                        NEW.record_status <> 'VOIDED' OR NEW.void_reason IS NULL OR
                        NEW.status <> 'CANCELLED' OR NEW.cancelled_at IS NULL OR
                        NEW.consultation_id <> OLD.consultation_id OR
                        NEW.visit_id <> OLD.visit_id OR
                        NEW.clinic_id <> OLD.clinic_id OR
                        NEW.prescribed_by <> OLD.prescribed_by OR
                        NEW.dispensed_by <> OLD.dispensed_by OR
                        NEW.drug_name <> OLD.drug_name OR
                        NEW.dosage <> OLD.dosage OR
                        NEW.frequency <> OLD.frequency OR
                        NEW.duration <> OLD.duration OR
                        NEW.instructions <> OLD.instructions OR
                        NEW.issued_at <> OLD.issued_at OR
                        NEW.dispensed_at <> OLD.dispensed_at OR
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
                CREATE OR REPLACE FUNCTION prescriptions_block_delete_signed()
                RETURNS trigger AS $$
                BEGIN
                    IF OLD.record_status IN ('SIGNED', 'VOIDED') THEN
                        RAISE EXCEPTION 'signed record immutable';
                    END IF;
                    RETURN OLD;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
            op.execute(
                """
                CREATE TRIGGER prescriptions_block_update_signed
                BEFORE UPDATE ON prescriptions
                FOR EACH ROW
                EXECUTE FUNCTION prescriptions_block_update_signed();
                """
            )
            op.execute(
                """
                CREATE TRIGGER prescriptions_block_delete_signed
                BEFORE DELETE ON prescriptions
                FOR EACH ROW
                EXECUTE FUNCTION prescriptions_block_delete_signed();
                """
            )
        if table_exists("lab_results"):
            op.execute(
                """
                CREATE OR REPLACE FUNCTION lab_results_block_update_signed()
                RETURNS trigger AS $$
                BEGIN
                    IF OLD.record_status = 'VOIDED' THEN
                        RAISE EXCEPTION 'signed record immutable';
                    END IF;
                    IF OLD.record_status = 'SIGNED' AND (
                        NEW.record_status <> 'VOIDED' OR NEW.void_reason IS NULL OR
                        NEW.lab_request_id <> OLD.lab_request_id OR
                        NEW.clinic_id <> OLD.clinic_id OR
                        NEW.technician_id <> OLD.technician_id OR
                        NEW.result_value <> OLD.result_value OR
                        NEW.result_unit <> OLD.result_unit OR
                        NEW.reference_range <> OLD.reference_range OR
                        NEW.created_at <> OLD.created_at OR
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
                CREATE OR REPLACE FUNCTION lab_results_block_delete_signed()
                RETURNS trigger AS $$
                BEGIN
                    IF OLD.record_status IN ('SIGNED', 'VOIDED') THEN
                        RAISE EXCEPTION 'signed record immutable';
                    END IF;
                    RETURN OLD;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
            op.execute(
                """
                CREATE TRIGGER lab_results_block_update_signed
                BEFORE UPDATE ON lab_results
                FOR EACH ROW
                EXECUTE FUNCTION lab_results_block_update_signed();
                """
            )
            op.execute(
                """
                CREATE TRIGGER lab_results_block_delete_signed
                BEFORE DELETE ON lab_results
                FOR EACH ROW
                EXECUTE FUNCTION lab_results_block_delete_signed();
                """
            )


def downgrade() -> None:
    """Downgrade schema."""
    # No-op: corrective migration only adds missing structures.
