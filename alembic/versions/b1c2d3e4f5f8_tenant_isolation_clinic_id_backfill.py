"""tenant isolation clinic_id backfill

Revision ID: b1c2d3e4f5f8
Revises: a1b2c3d4e5f7
Create Date: 2026-01-27
"""

from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5f8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def _drop_sqlite_triggers(table_name: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {table_name}_block_update_signed;")
    op.execute(f"DROP TRIGGER IF EXISTS {table_name}_block_delete_signed;")


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

    def column_exists(table: str, column: str) -> bool:
        if bind.dialect.name == "postgresql":
            return (
                bind.execute(
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

    if dialect == "sqlite":
        for table in ("consultations", "prescriptions", "lab_results"):
            if table_exists(table):
                _drop_sqlite_triggers(table)
    else:
        for table in ("consultations", "prescriptions", "lab_results"):
            if table_exists(table):
                op.execute(f"ALTER TABLE {table} DISABLE TRIGGER USER;")

    # 1) add clinic_id nullable
    if table_exists("consultations") and not column_exists("consultations", "clinic_id"):
        with op.batch_alter_table("consultations") as batch:
            batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))
    if table_exists("lab_requests") and not column_exists("lab_requests", "clinic_id"):
        with op.batch_alter_table("lab_requests") as batch:
            batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))
    if table_exists("lab_results") and not column_exists("lab_results", "clinic_id"):
        with op.batch_alter_table("lab_results") as batch:
            batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))
    if table_exists("prescriptions") and not column_exists("prescriptions", "clinic_id"):
        with op.batch_alter_table("prescriptions") as batch:
            batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))
    if table_exists("dispensations") and not column_exists("dispensations", "clinic_id"):
        with op.batch_alter_table("dispensations") as batch:
            batch.add_column(sa.Column("clinic_id", sa.Uuid(), nullable=True))

    # 2) backfill
    if table_exists("consultations") and column_exists("consultations", "clinic_id"):
        op.execute(
            """
            UPDATE consultations
            SET clinic_id = (
                SELECT visits.clinic_id FROM visits
                WHERE visits.id = consultations.visit_id
            )
            WHERE clinic_id IS NULL;
            """
        )
    if table_exists("lab_requests") and column_exists("lab_requests", "clinic_id"):
        op.execute(
            """
            UPDATE lab_requests
            SET clinic_id = (
                SELECT visits.clinic_id FROM visits
                WHERE visits.id = lab_requests.visit_id
            )
            WHERE clinic_id IS NULL;
            """
        )
    if table_exists("lab_results") and column_exists("lab_results", "clinic_id"):
        op.execute(
            """
            UPDATE lab_results
            SET clinic_id = (
                SELECT lab_requests.clinic_id FROM lab_requests
                WHERE lab_requests.id = lab_results.lab_request_id
            )
            WHERE clinic_id IS NULL;
            """
        )
    if table_exists("prescriptions") and column_exists("prescriptions", "clinic_id"):
        op.execute(
            """
            UPDATE prescriptions
            SET clinic_id = (
                SELECT visits.clinic_id FROM visits
                WHERE visits.id = prescriptions.visit_id
            )
            WHERE clinic_id IS NULL;
            """
        )
    if table_exists("dispensations") and column_exists("dispensations", "clinic_id"):
        op.execute(
            """
            UPDATE dispensations
            SET clinic_id = (
                SELECT prescriptions.clinic_id FROM prescriptions
                WHERE prescriptions.id = dispensations.prescription_id
            )
            WHERE clinic_id IS NULL;
            """
        )

    # 2.5) add unique constraints required for composite FKs (skip on SQLite)
    if dialect != "sqlite":
        if table_exists("visits"):
            op.create_unique_constraint(
                "uq_visits_id_clinic",
                "visits",
                ["id", "clinic_id"],
            )
        if table_exists("lab_requests"):
            op.create_unique_constraint(
                "uq_lab_requests_id_clinic",
                "lab_requests",
                ["id", "clinic_id"],
            )
        if table_exists("prescriptions"):
            op.create_unique_constraint(
                "uq_prescriptions_id_clinic",
                "prescriptions",
                ["id", "clinic_id"],
            )

    # 3) set NOT NULL
    if table_exists("consultations") and column_exists("consultations", "clinic_id"):
        with op.batch_alter_table("consultations") as batch:
            batch.alter_column("clinic_id", nullable=False)
            batch.create_foreign_key(
                "fk_consultations_clinic_id",
                "clinics",
                ["clinic_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch.create_foreign_key(
                "fk_consultations_visit_clinic",
                "visits",
                ["visit_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )
    if table_exists("lab_requests") and column_exists("lab_requests", "clinic_id"):
        with op.batch_alter_table("lab_requests") as batch:
            batch.alter_column("clinic_id", nullable=False)
            batch.create_foreign_key(
                "fk_lab_requests_clinic_id",
                "clinics",
                ["clinic_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch.create_foreign_key(
                "fk_lab_requests_visit_clinic",
                "visits",
                ["visit_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )
    if table_exists("lab_results") and column_exists("lab_results", "clinic_id"):
        with op.batch_alter_table("lab_results") as batch:
            batch.alter_column("clinic_id", nullable=False)
            batch.create_foreign_key(
                "fk_lab_results_clinic_id",
                "clinics",
                ["clinic_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch.create_foreign_key(
                "fk_lab_results_request_clinic",
                "lab_requests",
                ["lab_request_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )
    if table_exists("prescriptions") and column_exists("prescriptions", "clinic_id"):
        with op.batch_alter_table("prescriptions") as batch:
            batch.alter_column("clinic_id", nullable=False)
            batch.create_foreign_key(
                "fk_prescriptions_clinic_id",
                "clinics",
                ["clinic_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch.create_foreign_key(
                "fk_prescriptions_visit_clinic",
                "visits",
                ["visit_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )
    if table_exists("dispensations") and column_exists("dispensations", "clinic_id"):
        with op.batch_alter_table("dispensations") as batch:
            batch.alter_column("clinic_id", nullable=False)
            batch.create_foreign_key(
                "fk_dispensations_clinic_id",
                "clinics",
                ["clinic_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch.create_foreign_key(
                "fk_dispensations_prescription_clinic",
                "prescriptions",
                ["prescription_id", "clinic_id"],
                ["id", "clinic_id"],
                ondelete="CASCADE",
            )

    if dialect == "sqlite":
        for table in ("consultations", "prescriptions", "lab_results"):
            if table_exists(table):
                _create_sqlite_triggers(table)
    else:
        for table in ("consultations", "prescriptions", "lab_results"):
            if table_exists(table):
                op.execute(f"ALTER TABLE {table} ENABLE TRIGGER USER;")


def downgrade() -> None:
    with op.batch_alter_table("dispensations") as batch:
        batch.drop_constraint("fk_dispensations_prescription_clinic", type_="foreignkey")
        batch.drop_constraint("fk_dispensations_clinic_id", type_="foreignkey")
        batch.drop_column("clinic_id")
    with op.batch_alter_table("prescriptions") as batch:
        batch.drop_constraint("fk_prescriptions_visit_clinic", type_="foreignkey")
        batch.drop_constraint("fk_prescriptions_clinic_id", type_="foreignkey")
        batch.drop_column("clinic_id")
    with op.batch_alter_table("lab_results") as batch:
        batch.drop_constraint("fk_lab_results_request_clinic", type_="foreignkey")
        batch.drop_constraint("fk_lab_results_clinic_id", type_="foreignkey")
        batch.drop_column("clinic_id")
    with op.batch_alter_table("lab_requests") as batch:
        batch.drop_constraint("fk_lab_requests_visit_clinic", type_="foreignkey")
        batch.drop_constraint("fk_lab_requests_clinic_id", type_="foreignkey")
        batch.drop_column("clinic_id")
    with op.batch_alter_table("consultations") as batch:
        batch.drop_constraint("fk_consultations_visit_clinic", type_="foreignkey")
        batch.drop_constraint("fk_consultations_clinic_id", type_="foreignkey")
        batch.drop_column("clinic_id")

    op.drop_constraint("uq_prescriptions_id_clinic", "prescriptions", type_="unique")
    op.drop_constraint("uq_lab_requests_id_clinic", "lab_requests", type_="unique")
    op.drop_constraint("uq_visits_id_clinic", "visits", type_="unique")
