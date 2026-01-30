"""phase3 clinical priority queue

Revision ID: f3c4d5e6a7b8
Revises: e2f3a4b5c6d7
Create Date: 2026-01-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f3c4d5e6a7b8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)

    if dialect == "postgresql":
        priority_level = postgresql.ENUM(
            "CRITICAL",
            "URGENT",
            "ROUTINE",
            name="clinical_priority_level",
            create_type=False,
        )
        priority_source = postgresql.ENUM(
            "TRIAGE",
            "CLINICIAN",
            "SYSTEM",
            name="clinical_priority_source",
            create_type=False,
        )
        priority_level.create(bind, checkfirst=True)
        priority_source.create(bind, checkfirst=True)
    else:
        priority_level = sa.Enum(
            "CRITICAL",
            "URGENT",
            "ROUTINE",
            name="clinical_priority_level",
        )
        priority_source = sa.Enum(
            "TRIAGE",
            "CLINICIAN",
            "SYSTEM",
            name="clinical_priority_source",
        )

    op.create_table(
        "clinical_priority_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("level", priority_level, nullable=False),
        sa.Column("source", priority_source, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("set_by", sa.Uuid(), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_priority_visit_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_priority_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_priority_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["set_by"],
            ["users.id"],
            name="fk_priority_set_by",
        ),
        sa.CheckConstraint(
            "length(reason) >= 3",
            name="ck_priority_reason_length",
        ),
    )

    def table_exists(name: str) -> bool:
        if dialect == "postgresql":
            return (
                bind.execute(
                    sa.text("SELECT to_regclass(:name)"),
                    {"name": f"public.{name}"},
                ).scalar()
                is not None
            )
        return name in inspector.get_table_names()

    if not table_exists("visit_status_history"):
        if dialect == "postgresql":
            visit_status_enum = postgresql.ENUM(
                "REGISTERED",
                "TRIAGED",
                "IN_CONSULTATION",
                "LAB_REQUESTED",
                "LAB_COMPLETED",
                "PHARMACY_PENDING",
                "COMPLETED",
                "CANCELLED",
                name="visit_status",
                create_type=False,
            )
        else:
            visit_status_enum = sa.Enum(
                "REGISTERED",
                "TRIAGED",
                "IN_CONSULTATION",
                "LAB_REQUESTED",
                "LAB_COMPLETED",
                "PHARMACY_PENDING",
                "COMPLETED",
                "CANCELLED",
                name="visit_status",
            )
        op.create_table(
            "visit_status_history",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("visit_id", sa.Uuid(), nullable=False),
            sa.Column(
                "from_status",
                visit_status_enum,
                nullable=False,
            ),
            sa.Column(
                "to_status",
                visit_status_enum,
                nullable=False,
            ),
            sa.Column("changed_by", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(
                ["visit_id"],
                ["visits.id"],
                name="visit_status_history_visit_id_fkey",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["changed_by"],
                ["users.id"],
                name="visit_status_history_changed_by_fkey",
            ),
        )

    existing_indexes = set()
    if table_exists("visit_status_history"):
        existing_indexes = {
            ix["name"] for ix in inspector.get_indexes("visit_status_history")
        }
    if "ix_visit_status_history_visit_status_created_at" not in existing_indexes:
        op.create_index(
            "ix_visit_status_history_visit_status_created_at",
            "visit_status_history",
            ["visit_id", "to_status", "created_at"],
        )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION clinical_priority_events_block_update_delete()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'clinical priority history is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER clinical_priority_events_block_update
            BEFORE UPDATE ON clinical_priority_events
            FOR EACH ROW
            EXECUTE FUNCTION clinical_priority_events_block_update_delete();
            """
        )
        op.execute(
            """
            CREATE TRIGGER clinical_priority_events_block_delete
            BEFORE DELETE ON clinical_priority_events
            FOR EACH ROW
            EXECUTE FUNCTION clinical_priority_events_block_update_delete();
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_priority_visit_set_at_desc
            ON clinical_priority_events (visit_id, set_at DESC);
            """
        )
    else:
        op.create_index(
            "ix_priority_visit_set_at_desc",
            "clinical_priority_events",
            ["visit_id", "set_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_priority_visit_set_at_desc")
        op.execute("DROP TRIGGER IF EXISTS clinical_priority_events_block_delete ON clinical_priority_events;")
        op.execute("DROP TRIGGER IF EXISTS clinical_priority_events_block_update ON clinical_priority_events;")
        op.execute("DROP FUNCTION IF EXISTS clinical_priority_events_block_update_delete;")
    else:
        op.drop_index("ix_priority_visit_set_at_desc", table_name="clinical_priority_events")

    if dialect != "sqlite":
        op.execute("DROP INDEX IF EXISTS ix_visit_status_history_visit_status_created_at")
    else:
        op.drop_index(
            "ix_visit_status_history_visit_status_created_at",
            table_name="visit_status_history",
        )
    op.drop_table("clinical_priority_events")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS clinical_priority_source")
        op.execute("DROP TYPE IF EXISTS clinical_priority_level")
