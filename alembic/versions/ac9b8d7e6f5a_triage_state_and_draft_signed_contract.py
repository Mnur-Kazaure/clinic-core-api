"""add triage state mirror and triage draft/signed status

Revision ID: ac9b8d7e6f5a
Revises: ab12cd34ef56
Create Date: 2026-02-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ac9b8d7e6f5a"
down_revision: Union[str, Sequence[str], None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _build_enum(name: str, values: tuple[str, ...], bind) -> sa.Enum:
    if bind.dialect.name == "postgresql":
        enum = postgresql.ENUM(*values, name=name, create_type=False)
        enum.create(bind, checkfirst=True)
        return enum
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    triage_record_status_enum = _build_enum(
        "triage_record_status",
        ("DRAFT", "SIGNED"),
        bind,
    )
    visit_triage_state_enum = _build_enum(
        "visit_triage_state",
        ("NOT_REQUIRED", "PENDING", "TRIAGED"),
        bind,
    )

    triage_columns = {col["name"] for col in inspector.get_columns("triage_assessments")}
    if "record_status" not in triage_columns:
        op.add_column(
            "triage_assessments",
            sa.Column(
                "record_status",
                triage_record_status_enum,
                nullable=False,
                server_default="SIGNED",
            ),
        )

    visit_columns = {col["name"] for col in inspector.get_columns("visits")}
    if "triage_state" not in visit_columns:
        op.add_column(
            "visits",
            sa.Column(
                "triage_state",
                visit_triage_state_enum,
                nullable=False,
                server_default="PENDING",
            ),
        )
    if "triage_acuity" not in visit_columns:
        if bind.dialect.name == "postgresql":
            clinical_priority_enum = postgresql.ENUM(
                "CRITICAL",
                "URGENT",
                "ROUTINE",
                name="clinical_priority_level",
                create_type=False,
            )
            clinical_priority_enum.create(bind, checkfirst=True)
        else:
            clinical_priority_enum = sa.Enum(
                "CRITICAL",
                "URGENT",
                "ROUTINE",
                name="clinical_priority_level",
            )
        op.add_column("visits", sa.Column("triage_acuity", clinical_priority_enum, nullable=True))
    if "triaged_at" not in visit_columns:
        op.add_column("visits", sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True))
    if "triaged_by" not in visit_columns:
        op.add_column("visits", sa.Column("triaged_by", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_visits_triaged_by_user",
            "visits",
            "users",
            ["triaged_by"],
            ["id"],
        )

    # Backfill existing signed assessments as TRIAGED mirror state on visits.
    bind.execute(
        sa.text(
            """
            UPDATE visits
            SET
              triage_state = 'TRIAGED',
              triage_acuity = (
                SELECT ta.acuity_level
                FROM triage_assessments ta
                WHERE ta.visit_id = visits.id
                  AND ta.superseded_at IS NULL
                ORDER BY ta.created_at DESC, ta.id DESC
                LIMIT 1
              ),
              triaged_at = (
                SELECT ta.finalized_at
                FROM triage_assessments ta
                WHERE ta.visit_id = visits.id
                  AND ta.superseded_at IS NULL
                ORDER BY ta.created_at DESC, ta.id DESC
                LIMIT 1
              ),
              triaged_by = (
                SELECT ta.finalized_by
                FROM triage_assessments ta
                WHERE ta.visit_id = visits.id
                  AND ta.superseded_at IS NULL
                ORDER BY ta.created_at DESC, ta.id DESC
                LIMIT 1
              )
            WHERE EXISTS (
              SELECT 1
              FROM triage_assessments ta
              WHERE ta.visit_id = visits.id
                AND ta.superseded_at IS NULL
            )
            """
        )
    )

    # Completed/cancelled visits without triage are marked as not-required.
    bind.execute(
        sa.text(
            """
            UPDATE visits
            SET triage_state = 'NOT_REQUIRED'
            WHERE status IN ('COMPLETED', 'CANCELLED')
              AND (triaged_at IS NULL OR triage_acuity IS NULL)
            """
        )
    )

    # Draft should be the default for new triage assessments going forward.
    op.alter_column("triage_assessments", "record_status", server_default="DRAFT")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    visit_columns = {col["name"] for col in inspector.get_columns("visits")}
    if "triaged_by" in visit_columns:
        op.drop_constraint("fk_visits_triaged_by_user", "visits", type_="foreignkey")
        op.drop_column("visits", "triaged_by")
    if "triaged_at" in visit_columns:
        op.drop_column("visits", "triaged_at")
    if "triage_acuity" in visit_columns:
        op.drop_column("visits", "triage_acuity")
    if "triage_state" in visit_columns:
        op.drop_column("visits", "triage_state")

    triage_columns = {col["name"] for col in inspector.get_columns("triage_assessments")}
    if "record_status" in triage_columns:
        op.drop_column("triage_assessments", "record_status")

    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="visit_triage_state").drop(bind, checkfirst=True)
        postgresql.ENUM(name="triage_record_status").drop(bind, checkfirst=True)
