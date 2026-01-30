"""update immutability triggers for voided records

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5f8
Create Date: 2026-01-27
"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4g5h6"
down_revision = "b1c2d3e4f5f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)

    def table_exists(name: str) -> bool:
        if bind.dialect.name == "postgresql":
            return (
                bind.execute(
                    sa.text("SELECT to_regclass(:name)"),
                    {"name": f"public.{name}"},
                ).scalar()
                is not None
            )
        return name in inspector.get_table_names()

    if dialect == "sqlite":
        for table in ("consultations", "prescriptions", "lab_results"):
            if table_exists(table):
                op.execute(f"DROP TRIGGER IF EXISTS {table}_block_update_signed;")
                op.execute(f"DROP TRIGGER IF EXISTS {table}_block_delete_signed;")
        # Triggers will be re-created by application helpers in tests if needed.
        return

    for table in ("consultations", "prescriptions", "lab_results"):
        if table_exists(table):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_block_update_signed ON {table};")
            op.execute(f"DROP TRIGGER IF EXISTS {table}_block_delete_signed ON {table};")
            op.execute(f"DROP FUNCTION IF EXISTS {table}_block_update_signed();")
            op.execute(f"DROP FUNCTION IF EXISTS {table}_block_delete_signed();")

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

    for table in ("consultations", "prescriptions", "lab_results"):
        if table_exists(table):
            op.execute(
                f"""
                CREATE TRIGGER {table}_block_update_signed
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION {table}_block_update_signed();
                """
            )
            op.execute(
                f"""
                CREATE TRIGGER {table}_block_delete_signed
                BEFORE DELETE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION {table}_block_delete_signed();
                """
            )


def downgrade() -> None:
    # No-op: previous migration defines original triggers.
    pass
