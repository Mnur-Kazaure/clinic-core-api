"""add record status and immutability triggers

Revision ID: f1b2c3d4e5f6
Revises: ef3b1c2c7e2a
Create Date: 2026-01-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1b2c3d4e5f6"
down_revision = "ef3b1c2c7e2a"
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    if conn.dialect.name == "postgresql":
        return (
            conn.execute(
                sa.text("SELECT to_regclass(:name)"),
                {"name": f"public.{table_name}"},
            ).scalar()
            is not None
        )
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
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
                {"table_name": table_name, "column_name": column_name},
            ).scalar()
            is not None
        )
    inspector = sa.inspect(conn)
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _columns_exist(conn, table_name: str, columns: list[str]) -> bool:
    return all(_column_exists(conn, table_name, column) for column in columns)


def _create_sqlite_triggers(table_name: str) -> None:
    if table_name == "consultations":
        immutable_checks = """
            NEW.visit_id != OLD.visit_id OR
            NEW.clinic_id != OLD.clinic_id OR
            NEW.doctor_id != OLD.doctor_id OR
            NEW.started_at != OLD.started_at OR
            NEW.completed_at != OLD.completed_at OR
            NEW.vitals != OLD.vitals OR
            NEW.presenting_complaints != OLD.presenting_complaints OR
            NEW.diagnosis != OLD.diagnosis OR
            NEW.notes != OLD.notes OR
            NEW.doctor_full_name != OLD.doctor_full_name OR
            NEW.signed_at != OLD.signed_at
        """
        void_checks = "NEW.record_status != 'VOIDED' OR NEW.void_reason IS NULL OR " + immutable_checks
    elif table_name == "prescriptions":
        immutable_checks = """
            NEW.consultation_id != OLD.consultation_id OR
            NEW.visit_id != OLD.visit_id OR
            NEW.clinic_id != OLD.clinic_id OR
            NEW.prescribed_by != OLD.prescribed_by OR
            NEW.dispensed_by != OLD.dispensed_by OR
            NEW.drug_name != OLD.drug_name OR
            NEW.dosage != OLD.dosage OR
            NEW.frequency != OLD.frequency OR
            NEW.duration != OLD.duration OR
            NEW.instructions != OLD.instructions OR
            NEW.issued_at != OLD.issued_at OR
            NEW.dispensed_at != OLD.dispensed_at OR
            NEW.signed_at != OLD.signed_at
        """
        void_checks = (
            "NEW.record_status != 'VOIDED' OR NEW.void_reason IS NULL OR "
            "NEW.status != 'CANCELLED' OR NEW.cancelled_at IS NULL OR " + immutable_checks
        )
    else:
        immutable_checks = """
            NEW.lab_request_id != OLD.lab_request_id OR
            NEW.clinic_id != OLD.clinic_id OR
            NEW.technician_id != OLD.technician_id OR
            NEW.result_value != OLD.result_value OR
            NEW.result_unit != OLD.result_unit OR
            NEW.reference_range != OLD.reference_range OR
            NEW.created_at != OLD.created_at OR
            NEW.signed_at != OLD.signed_at
        """
        void_checks = "NEW.record_status != 'VOIDED' OR NEW.void_reason IS NULL OR " + immutable_checks

    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS {table_name}_block_update_signed
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW
        WHEN OLD.record_status = 'SIGNED' AND ({void_checks})
        BEGIN
            SELECT RAISE(ABORT, 'signed record immutable');
        END;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS {table_name}_block_delete_signed
        BEFORE DELETE ON {table_name}
        FOR EACH ROW
        WHEN OLD.record_status = 'SIGNED'
        BEGIN
            SELECT RAISE(ABORT, 'signed record immutable');
        END;
        """
    )

def _drop_sqlite_triggers(table_name: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {table_name}_block_update_signed;")
    op.execute(f"DROP TRIGGER IF EXISTS {table_name}_block_delete_signed;")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    record_status_enum = sa.Enum(
        "DRAFT",
        "SIGNED",
        "AMENDED",
        "VOIDED",
        name="record_status",
    )
    if dialect != "sqlite":
        record_status_enum.create(bind, checkfirst=True)

    if _table_exists(bind, "consultations"):
        columns = {col["name"] for col in inspector.get_columns("consultations")}
        existing_checks = {
            ck["name"] for ck in inspector.get_check_constraints("consultations")
        }
        with op.batch_alter_table("consultations") as batch:
            if "record_status" not in columns:
                batch.add_column(
                    sa.Column(
                        "record_status",
                        record_status_enum,
                        nullable=False,
                        server_default="DRAFT",
                    )
                )
            if "signed_at" not in columns:
                batch.add_column(sa.Column("signed_at", sa.DateTime(timezone=True)))
            if "void_reason" not in columns:
                batch.add_column(sa.Column("void_reason", sa.Text(), nullable=True))
            if "ck_consultations_void_reason" not in existing_checks:
                batch.create_check_constraint(
                    "ck_consultations_void_reason",
                    "(record_status != 'VOIDED') OR (void_reason IS NOT NULL)",
                )

    if _table_exists(bind, "prescriptions"):
        columns = {col["name"] for col in inspector.get_columns("prescriptions")}
        existing_checks = {
            ck["name"] for ck in inspector.get_check_constraints("prescriptions")
        }
        with op.batch_alter_table("prescriptions") as batch:
            if "record_status" not in columns:
                batch.add_column(
                    sa.Column(
                        "record_status",
                        record_status_enum,
                        nullable=False,
                        server_default="DRAFT",
                    )
                )
            if "signed_at" not in columns:
                batch.add_column(sa.Column("signed_at", sa.DateTime(timezone=True)))
            if "void_reason" not in columns:
                batch.add_column(
                    sa.Column("void_reason", sa.String(length=255), nullable=True)
                )
            if "ck_prescriptions_void_reason" not in existing_checks:
                batch.create_check_constraint(
                    "ck_prescriptions_void_reason",
                    "(record_status != 'VOIDED') OR (void_reason IS NOT NULL)",
                )

    if _table_exists(bind, "lab_results"):
        columns = {col["name"] for col in inspector.get_columns("lab_results")}
        existing_checks = {
            ck["name"] for ck in inspector.get_check_constraints("lab_results")
        }
        with op.batch_alter_table("lab_results") as batch:
            if "record_status" not in columns:
                batch.add_column(
                    sa.Column(
                        "record_status",
                        record_status_enum,
                        nullable=False,
                        server_default="DRAFT",
                    )
                )
            if "signed_at" not in columns:
                batch.add_column(sa.Column("signed_at", sa.DateTime(timezone=True)))
            if "void_reason" not in columns:
                batch.add_column(
                    sa.Column("void_reason", sa.String(length=255), nullable=True)
                )
            if "ck_lab_results_void_reason" not in existing_checks:
                batch.create_check_constraint(
                    "ck_lab_results_void_reason",
                    "(record_status != 'VOIDED') OR (void_reason IS NOT NULL)",
                )

    if _table_exists(bind, "consultations") and _column_exists(
        bind, "consultations", "completed_at"
    ):
        op.execute(
            "UPDATE consultations SET record_status='SIGNED', signed_at=completed_at "
            "WHERE completed_at IS NOT NULL;"
        )
    if _table_exists(bind, "prescriptions") and _column_exists(
        bind, "prescriptions", "issued_at"
    ):
        op.execute(
            "UPDATE prescriptions SET record_status='SIGNED', signed_at=issued_at "
            "WHERE issued_at IS NOT NULL;"
        )
    if _table_exists(bind, "lab_results"):
        op.execute(
            "UPDATE lab_results SET record_status='SIGNED', signed_at=created_at "
            "WHERE created_at IS NOT NULL;"
        )

    if dialect == "sqlite":
        if _table_exists(bind, "consultations") and _columns_exist(
            bind,
            "consultations",
            [
                "visit_id",
                "clinic_id",
                "doctor_id",
                "started_at",
                "completed_at",
                "vitals",
                "presenting_complaints",
                "diagnosis",
                "notes",
                "doctor_full_name",
                "signed_at",
                "record_status",
                "void_reason",
            ],
        ):
            _create_sqlite_triggers("consultations")
        if _table_exists(bind, "prescriptions") and _columns_exist(
            bind,
            "prescriptions",
            [
                "consultation_id",
                "visit_id",
                "clinic_id",
                "prescribed_by",
                "dispensed_by",
                "drug_name",
                "dosage",
                "frequency",
                "duration",
                "instructions",
                "issued_at",
                "dispensed_at",
                "signed_at",
                "status",
                "cancelled_at",
                "record_status",
                "void_reason",
            ],
        ):
            _create_sqlite_triggers("prescriptions")
        if _table_exists(bind, "lab_results") and _columns_exist(
            bind,
            "lab_results",
            [
                "lab_request_id",
                "clinic_id",
                "technician_id",
                "result_value",
                "result_unit",
                "reference_range",
                "created_at",
                "signed_at",
                "record_status",
                "void_reason",
            ],
        ):
            _create_sqlite_triggers("lab_results")
    else:
        if _table_exists(bind, "consultations"):
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
                    IF OLD.record_status = 'SIGNED' THEN
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
        if _table_exists(bind, "prescriptions"):
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
                    IF OLD.record_status = 'SIGNED' THEN
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
        if _table_exists(bind, "lab_results"):
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
                    IF OLD.record_status = 'SIGNED' THEN
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
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        for table in ("consultations", "prescriptions", "lab_results"):
            _drop_sqlite_triggers(table)
    else:
        for table in ("consultations", "prescriptions", "lab_results"):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_block_update_signed ON {table};")
            op.execute(f"DROP TRIGGER IF EXISTS {table}_block_delete_signed ON {table};")
            op.execute(f"DROP FUNCTION IF EXISTS {table}_block_update_signed();")
            op.execute(f"DROP FUNCTION IF EXISTS {table}_block_delete_signed();")

    with op.batch_alter_table("consultations") as batch:
        batch.drop_constraint("ck_consultations_void_reason", type_="check")
        batch.drop_column("signed_at")
        batch.drop_column("void_reason")
        batch.drop_column("record_status")

    with op.batch_alter_table("prescriptions") as batch:
        batch.drop_constraint("ck_prescriptions_void_reason", type_="check")
        batch.drop_column("signed_at")
        batch.drop_column("void_reason")
        batch.drop_column("record_status")

    with op.batch_alter_table("lab_results") as batch:
        batch.drop_constraint("ck_lab_results_void_reason", type_="check")
        batch.drop_column("signed_at")
        batch.drop_column("void_reason")
        batch.drop_column("record_status")

    if dialect != "sqlite":
        record_status_enum = sa.Enum(
            "DRAFT",
            "SIGNED",
            "AMENDED",
            "VOIDED",
            name="record_status",
        )
        record_status_enum.drop(bind, checkfirst=True)
