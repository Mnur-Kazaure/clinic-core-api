"""phase5 break glass audit review

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-01-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PURPOSE_VALUES = (
    "TREATMENT",
    "OPERATIONS",
    "EMERGENCY",
    "AUDIT",
    "BILLING",
    "SECURITY",
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        purpose_of_use = postgresql.ENUM(*PURPOSE_VALUES, name="purpose_of_use", create_type=False)
        audit_case_status = postgresql.ENUM("OPEN", "IN_REVIEW", "CLOSED", name="audit_case_status", create_type=False)
        audit_case_severity = postgresql.ENUM("LOW", "MEDIUM", "HIGH", "CRITICAL", name="audit_case_severity", create_type=False)
        audit_case_outcome = postgresql.ENUM("JUSTIFIED", "UNJUSTIFIED", "TRAINING_REQUIRED", "ESCALATED", name="audit_case_outcome", create_type=False)
        audit_item_type = postgresql.ENUM("ACCESS_LOG", "EVENT_LOG", name="audit_item_type", create_type=False)
        purpose_of_use.create(bind, checkfirst=True)
        audit_case_status.create(bind, checkfirst=True)
        audit_case_severity.create(bind, checkfirst=True)
        audit_case_outcome.create(bind, checkfirst=True)
        audit_item_type.create(bind, checkfirst=True)
    else:
        purpose_of_use = sa.Enum(*PURPOSE_VALUES, name="purpose_of_use")
        audit_case_status = sa.Enum("OPEN", "IN_REVIEW", "CLOSED", name="audit_case_status")
        audit_case_severity = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="audit_case_severity")
        audit_case_outcome = sa.Enum("JUSTIFIED", "UNJUSTIFIED", "TRAINING_REQUIRED", "ESCALATED", name="audit_case_outcome")
        audit_item_type = sa.Enum("ACCESS_LOG", "EVENT_LOG", name="audit_item_type")

    # access_logs: rename reason -> justification and add resource
    if dialect == "postgresql":
        op.execute("ALTER TABLE access_logs RENAME COLUMN reason TO justification")
    else:
        with op.batch_alter_table("access_logs") as batch:
            batch.alter_column("reason", new_column_name="justification")

    op.add_column("access_logs", sa.Column("resource", sa.String(length=100), nullable=True))

    # backfill defaults (non-destructive)
    allowed_values = ", ".join(f"'{value}'" for value in PURPOSE_VALUES)
    op.execute(
        "UPDATE access_logs SET purpose_of_use='OPERATIONS' "
        "WHERE purpose_of_use IS NULL OR purpose_of_use NOT IN (" + allowed_values + ")"
    )
    op.execute("UPDATE access_logs SET resource='SYSTEM' WHERE resource IS NULL")
    op.execute(
        "UPDATE access_logs SET justification='legacy access log backfill' "
        "WHERE break_glass = true AND (justification IS NULL OR length(justification) < 10)"
    )

    if dialect == "postgresql":
        op.execute("ALTER TABLE access_logs ALTER COLUMN purpose_of_use TYPE purpose_of_use USING purpose_of_use::text::purpose_of_use")
        op.execute("ALTER TABLE access_logs ALTER COLUMN purpose_of_use SET NOT NULL")
        op.execute("ALTER TABLE access_logs ALTER COLUMN justification SET NOT NULL")
        op.execute("ALTER TABLE access_logs ALTER COLUMN resource SET NOT NULL")
        op.execute(
            "ALTER TABLE access_logs ADD CONSTRAINT ck_access_logs_break_glass_justification "
            "CHECK (break_glass = false OR char_length(justification) >= 10)"
        )
    else:
        with op.batch_alter_table("access_logs") as batch:
            batch.alter_column("purpose_of_use", nullable=False)
            batch.alter_column("justification", nullable=False)
            batch.alter_column("resource", nullable=False)
            batch.create_check_constraint(
                "ck_access_logs_break_glass_justification",
                "break_glass = 0 OR length(justification) >= 10",
            )

    op.create_unique_constraint("uq_access_logs_id_clinic", "access_logs", ["id", "clinic_id"])
    op.create_unique_constraint("uq_event_log_id_clinic", "event_log", ["id", "clinic_id"])

    op.create_index(
        "ix_access_logs_clinic_created_break_glass",
        "access_logs",
        ["clinic_id", "created_at", "break_glass"],
    )
    op.create_index(
        "ix_access_logs_patient_created",
        "access_logs",
        ["patient_id", "created_at"],
    )

    # audit_review_cases
    op.create_table(
        "audit_review_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("status", audit_case_status, nullable=False),
        sa.Column("severity", audit_case_severity, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("closed_by", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", audit_case_outcome, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("id", "clinic_id", name="uq_audit_review_cases_id_clinic"),
        sa.CheckConstraint(
            "(status != 'IN_REVIEW') OR (reviewed_by IS NOT NULL)",
            name="ck_audit_case_reviewed_by",
        ),
        sa.CheckConstraint(
            "(status != 'CLOSED') OR (closed_by IS NOT NULL AND closed_at IS NOT NULL AND outcome IS NOT NULL)",
            name="ck_audit_case_closed_fields",
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_audit_review_case_clinic", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_audit_review_case_created_by"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_audit_review_case_reviewed_by"),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"], name="fk_audit_review_case_closed_by"),
    )

    op.create_index(
        "ix_audit_review_cases_clinic_status_created",
        "audit_review_cases",
        ["clinic_id", "status", "created_at"],
    )

    # audit_review_items
    op.create_table(
        "audit_review_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", audit_item_type, nullable=False),
        sa.Column("access_log_id", sa.Uuid(), nullable=True),
        sa.Column("event_log_id", sa.Uuid(), nullable=True),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(item_type = 'ACCESS_LOG' AND access_log_id IS NOT NULL AND event_log_id IS NULL) OR "
            "(item_type = 'EVENT_LOG' AND event_log_id IS NOT NULL AND access_log_id IS NULL)",
            name="ck_audit_review_item_type",
        ),
        sa.ForeignKeyConstraint(["case_id", "clinic_id"], ["audit_review_cases.id", "audit_review_cases.clinic_id"], name="fk_audit_review_item_case", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["access_log_id", "clinic_id"], ["access_logs.id", "access_logs.clinic_id"], name="fk_audit_review_item_access_log", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_log_id", "clinic_id"], ["event_log.id", "event_log.clinic_id"], name="fk_audit_review_item_event_log", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_audit_review_item_clinic", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], name="fk_audit_review_item_added_by"),
    )

    op.create_index(
        "ix_audit_review_items_case_added",
        "audit_review_items",
        ["case_id", "added_at"],
    )

    # audit_review_case_history
    op.create_table(
        "audit_review_case_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", audit_case_status, nullable=True),
        sa.Column("to_status", audit_case_status, nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id", "clinic_id"], ["audit_review_cases.id", "audit_review_cases.clinic_id"], name="fk_audit_review_history_case", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_audit_review_history_clinic", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], name="fk_audit_review_history_changed_by"),
    )

    if dialect == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION audit_review_items_block_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_review_items are append-only';
END;
$$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
CREATE TRIGGER audit_review_items_block_mutation
BEFORE UPDATE OR DELETE ON audit_review_items
FOR EACH ROW EXECUTE FUNCTION audit_review_items_block_mutation();
            """
        )
        op.execute(
            """
CREATE OR REPLACE FUNCTION audit_review_case_history_block_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_review_case_history is append-only';
END;
$$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
CREATE TRIGGER audit_review_case_history_block_mutation
BEFORE UPDATE OR DELETE ON audit_review_case_history
FOR EACH ROW EXECUTE FUNCTION audit_review_case_history_block_mutation();
            """
        )
    else:
        op.execute(
            """
CREATE TRIGGER audit_review_items_block_update
BEFORE UPDATE ON audit_review_items
BEGIN
    SELECT RAISE(FAIL, 'audit_review_items are append-only');
END;
            """
        )
        op.execute(
            """
CREATE TRIGGER audit_review_items_block_delete
BEFORE DELETE ON audit_review_items
BEGIN
    SELECT RAISE(FAIL, 'audit_review_items are append-only');
END;
            """
        )
        op.execute(
            """
CREATE TRIGGER audit_review_case_history_block_update
BEFORE UPDATE ON audit_review_case_history
BEGIN
    SELECT RAISE(FAIL, 'audit_review_case_history is append-only');
END;
            """
        )
        op.execute(
            """
CREATE TRIGGER audit_review_case_history_block_delete
BEFORE DELETE ON audit_review_case_history
BEGIN
    SELECT RAISE(FAIL, 'audit_review_case_history is append-only');
END;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_review_case_history_block_mutation ON audit_review_case_history")
        op.execute("DROP FUNCTION IF EXISTS audit_review_case_history_block_mutation")
        op.execute("DROP TRIGGER IF EXISTS audit_review_items_block_mutation ON audit_review_items")
        op.execute("DROP FUNCTION IF EXISTS audit_review_items_block_mutation")
    else:
        op.execute("DROP TRIGGER IF EXISTS audit_review_items_block_update")
        op.execute("DROP TRIGGER IF EXISTS audit_review_items_block_delete")
        op.execute("DROP TRIGGER IF EXISTS audit_review_case_history_block_update")
        op.execute("DROP TRIGGER IF EXISTS audit_review_case_history_block_delete")

    op.drop_index("ix_audit_review_items_case_added", table_name="audit_review_items")
    op.drop_index("ix_audit_review_cases_clinic_status_created", table_name="audit_review_cases")
    op.drop_index("ix_access_logs_patient_created", table_name="access_logs")
    op.drop_index("ix_access_logs_clinic_created_break_glass", table_name="access_logs")

    op.drop_table("audit_review_case_history")
    op.drop_table("audit_review_items")
    op.drop_table("audit_review_cases")

    op.drop_constraint("uq_event_log_id_clinic", "event_log", type_="unique")
    op.drop_constraint("uq_access_logs_id_clinic", "access_logs", type_="unique")

    if dialect == "postgresql":
        op.execute("ALTER TABLE access_logs DROP CONSTRAINT IF EXISTS ck_access_logs_break_glass_justification")
    else:
        with op.batch_alter_table("access_logs") as batch:
            batch.drop_constraint("ck_access_logs_break_glass_justification", type_="check")

    if dialect == "postgresql":
        op.execute("ALTER TABLE access_logs ALTER COLUMN purpose_of_use TYPE VARCHAR(100) USING purpose_of_use::text")

    op.execute("UPDATE access_logs SET resource=NULL")
    op.execute("UPDATE access_logs SET justification=NULL")

    if dialect == "postgresql":
        op.execute("ALTER TABLE access_logs RENAME COLUMN justification TO reason")
    else:
        with op.batch_alter_table("access_logs") as batch:
            batch.alter_column("justification", new_column_name="reason")

    op.drop_column("access_logs", "resource")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS audit_item_type")
        op.execute("DROP TYPE IF EXISTS audit_case_outcome")
        op.execute("DROP TYPE IF EXISTS audit_case_severity")
        op.execute("DROP TYPE IF EXISTS audit_case_status")
        op.execute("DROP TYPE IF EXISTS purpose_of_use")
