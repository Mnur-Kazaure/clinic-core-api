"""phase B follow-up generation and missed lifecycle

Revision ID: f4c8b2d1a6e9
Revises: e7b3c2a1d9f4
Create Date: 2026-02-16 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f4c8b2d1a6e9"
down_revision = "e7b3c2a1d9f4"
branch_labels = None
depends_on = None


def _create_enum_if_needed(bind, enum_type: sa.Enum) -> None:
    if bind.dialect.name == "postgresql":
        enum_type.create(bind, checkfirst=True)


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        follow_up_type = postgresql.ENUM(
            "MANUAL",
            "POST_DISCHARGE",
            "LAB_REVIEW",
            "ANC_REVIEW",
            "CHRONIC_RECALL",
            name="follow_up_type",
            create_type=False,
        )
        follow_up_status = postgresql.ENUM(
            "SCHEDULED",
            "COMPLETED",
            "MISSED",
            "CANCELLED",
            name="follow_up_status",
            create_type=False,
        )
        follow_up_generated_by = postgresql.ENUM(
            "USER",
            "SYSTEM",
            name="follow_up_generated_by",
            create_type=False,
        )
        follow_up_priority = postgresql.ENUM(
            "ROUTINE",
            "IMPORTANT",
            "CRITICAL",
            name="follow_up_priority",
            create_type=False,
        )
    else:
        follow_up_type = sa.Enum(
            "MANUAL",
            "POST_DISCHARGE",
            "LAB_REVIEW",
            "ANC_REVIEW",
            "CHRONIC_RECALL",
            name="follow_up_type",
        )
        follow_up_status = sa.Enum(
            "SCHEDULED",
            "COMPLETED",
            "MISSED",
            "CANCELLED",
            name="follow_up_status",
        )
        follow_up_generated_by = sa.Enum(
            "USER",
            "SYSTEM",
            name="follow_up_generated_by",
        )
        follow_up_priority = sa.Enum(
            "ROUTINE",
            "IMPORTANT",
            "CRITICAL",
            name="follow_up_priority",
        )

    _create_enum_if_needed(bind, follow_up_type)
    _create_enum_if_needed(bind, follow_up_status)
    _create_enum_if_needed(bind, follow_up_generated_by)
    _create_enum_if_needed(bind, follow_up_priority)

    op.create_table(
        "follow_ups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id_canonical", sa.UUID(), nullable=False),
        sa.Column("type", follow_up_type, nullable=False),
        sa.Column("priority", follow_up_priority, nullable=False),
        sa.Column("status", follow_up_status, nullable=False, server_default="SCHEDULED"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("origin_visit_id", sa.UUID(), nullable=True),
        sa.Column("origin_admission_id", sa.UUID(), nullable=True),
        sa.Column("chronic_recall_id", sa.UUID(), nullable=True),
        sa.Column("completed_visit_id", sa.UUID(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason_code", sa.String(length=64), nullable=True),
        sa.Column("cancel_reason_text", sa.String(length=500), nullable=True),
        sa.Column("generated_by", follow_up_generated_by, nullable=False, server_default="USER"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("rescheduled_from_id", sa.UUID(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "clinic_id", name="uq_follow_ups_id_clinic"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_follow_ups_clinic_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id_canonical", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_follow_ups_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_follow_ups_owner_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["origin_visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_follow_ups_origin_visit_clinic",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["completed_visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_follow_ups_completed_visit_clinic",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["origin_admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_follow_ups_origin_admission_clinic",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["chronic_recall_id"],
            ["chronic_recalls.id"],
            name="fk_follow_ups_chronic_recall_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_follow_ups_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["rescheduled_from_id"],
            ["follow_ups.id"],
            name="fk_follow_ups_rescheduled_from_id",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "(status != 'COMPLETED') OR "
            "(completed_visit_id IS NOT NULL AND completed_at IS NOT NULL)",
            name="ck_follow_ups_completed_requires_visit_and_timestamp",
        ),
    )
    op.create_index(
        "ix_follow_ups_clinic_status_due_at",
        "follow_ups",
        ["clinic_id", "status", "due_at"],
    )
    op.create_index(
        "ix_follow_ups_clinic_chronic_recall",
        "follow_ups",
        ["clinic_id", "chronic_recall_id"],
    )
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_follow_ups_chronic_recall_scheduled",
            "follow_ups",
            ["clinic_id", "chronic_recall_id"],
            unique=True,
            postgresql_where=sa.text(
                "type = 'CHRONIC_RECALL' AND status = 'SCHEDULED' "
                "AND chronic_recall_id IS NOT NULL"
            ),
        )
    else:
        op.create_index(
            "uq_follow_ups_chronic_recall_scheduled",
            "follow_ups",
            ["clinic_id", "chronic_recall_id"],
            unique=True,
            sqlite_where=sa.text(
                "type = 'CHRONIC_RECALL' AND status = 'SCHEDULED' "
                "AND chronic_recall_id IS NOT NULL"
            ),
        )

    op.create_table(
        "follow_up_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("follow_up_id", sa.UUID(), nullable=False),
        sa.Column("old_status", follow_up_status, nullable=False),
        sa.Column("new_status", follow_up_status, nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["follow_up_id"],
            ["follow_ups.id"],
            name="fk_follow_up_status_history_follow_up_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_follow_up_status_history_actor_user_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_follow_up_status_history_follow_up_id",
        "follow_up_status_history",
        ["follow_up_id"],
    )

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION follow_up_status_history_block_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'follow_up_status_history is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER follow_up_status_history_block_update
            BEFORE UPDATE ON follow_up_status_history
            FOR EACH ROW
            EXECUTE FUNCTION follow_up_status_history_block_mutation();
            """
        )
        op.execute(
            """
            CREATE TRIGGER follow_up_status_history_block_delete
            BEFORE DELETE ON follow_up_status_history
            FOR EACH ROW
            EXECUTE FUNCTION follow_up_status_history_block_mutation();
            """
        )
    else:
        op.execute(
            """
            CREATE TRIGGER follow_up_status_history_block_update
            BEFORE UPDATE ON follow_up_status_history
            BEGIN
                SELECT RAISE(FAIL, 'follow_up_status_history is append-only');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER follow_up_status_history_block_delete
            BEFORE DELETE ON follow_up_status_history
            BEGIN
                SELECT RAISE(FAIL, 'follow_up_status_history is append-only');
            END;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS follow_up_status_history_block_delete "
            "ON follow_up_status_history"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS follow_up_status_history_block_update "
            "ON follow_up_status_history"
        )
        op.execute("DROP FUNCTION IF EXISTS follow_up_status_history_block_mutation")
    else:
        op.execute("DROP TRIGGER IF EXISTS follow_up_status_history_block_delete")
        op.execute("DROP TRIGGER IF EXISTS follow_up_status_history_block_update")

    op.drop_index(
        "ix_follow_up_status_history_follow_up_id",
        table_name="follow_up_status_history",
    )
    op.drop_table("follow_up_status_history")

    op.drop_index("uq_follow_ups_chronic_recall_scheduled", table_name="follow_ups")
    op.drop_index("ix_follow_ups_clinic_chronic_recall", table_name="follow_ups")
    op.drop_index("ix_follow_ups_clinic_status_due_at", table_name="follow_ups")
    op.drop_table("follow_ups")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS follow_up_generated_by")
        op.execute("DROP TYPE IF EXISTS follow_up_status")
        op.execute("DROP TYPE IF EXISTS follow_up_type")
