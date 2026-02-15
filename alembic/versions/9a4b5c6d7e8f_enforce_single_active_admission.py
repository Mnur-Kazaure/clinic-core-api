"""enforce single active admission per patient

Revision ID: 9a4b5c6d7e8f
Revises: 8b2c3d4e5f6a
Create Date: 2026-02-12 15:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a4b5c6d7e8f"
down_revision: Union[str, Sequence[str], None] = "8b2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "uq_admissions_active_patient"


def _index_exists(indexes: list[dict], name: str) -> bool:
    return any(index.get("name") == name for index in indexes)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes("admissions")
    if _index_exists(indexes, INDEX_NAME):
        return

    # Backfill safety: collapse legacy duplicate ACTIVE admissions per patient/clinic.
    # Keep the most recent ACTIVE row and cancel older duplicates so the partial
    # unique index can be created deterministically.
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            WITH ranked AS (
              SELECT
                id,
                row_number() OVER (
                  PARTITION BY clinic_id, patient_id
                  ORDER BY admitted_at DESC, created_at DESC, id DESC
                ) AS rn
              FROM admissions
              WHERE status = 'ACTIVE'
            )
            UPDATE admissions AS a
            SET
              status = 'CANCELLED',
              cancelled_at = COALESCE(a.cancelled_at, now()),
              cancel_reason = COALESCE(
                a.cancel_reason,
                'Auto-cancelled by migration (duplicate active admission)'
              )
            FROM ranked
            WHERE a.id = ranked.id
              AND ranked.rn > 1
            """
        )
    else:
        op.execute(
            """
            WITH ranked AS (
              SELECT
                id,
                row_number() OVER (
                  PARTITION BY clinic_id, patient_id
                  ORDER BY admitted_at DESC, created_at DESC, id DESC
                ) AS rn
              FROM admissions
              WHERE status = 'ACTIVE'
            )
            UPDATE admissions
            SET
              status = 'CANCELLED',
              cancelled_at = COALESCE(cancelled_at, CURRENT_TIMESTAMP),
              cancel_reason = COALESCE(
                cancel_reason,
                'Auto-cancelled by migration (duplicate active admission)'
              )
            WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
            """
        )

    if bind.dialect.name == "postgresql":
        op.create_index(
            INDEX_NAME,
            "admissions",
            ["clinic_id", "patient_id"],
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        )
        return

    op.create_index(
        INDEX_NAME,
        "admissions",
        ["clinic_id", "patient_id"],
        unique=True,
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes("admissions")
    if _index_exists(indexes, INDEX_NAME):
        op.drop_index(INDEX_NAME, table_name="admissions")
