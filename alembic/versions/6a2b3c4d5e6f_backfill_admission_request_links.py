"""backfill admission request links

Revision ID: 6a2b3c4d5e6f
Revises: 5e1a2b3c4d5e
Create Date: 2026-02-11
"""

from typing import Sequence, Union

from alembic import op


revision: str = "6a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "5e1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Link legacy APPROVED requests that are still missing admission_id.
    # The update is deterministic and conservative:
    # - request must have exactly one ACTIVE admission candidate for same patient/clinic
    # - admission must not already be linked to another request
    # - if multiple requests compete for one admission, only the most recent request wins
    op.execute(
        """
        WITH candidate_links AS (
            SELECT
                ar.id AS request_id,
                a.id AS admission_id,
                row_number() OVER (
                    PARTITION BY ar.id
                    ORDER BY a.admitted_at DESC, a.id DESC
                ) AS request_rank,
                count(*) OVER (
                    PARTITION BY ar.id
                ) AS request_candidate_count,
                row_number() OVER (
                    PARTITION BY a.id
                    ORDER BY ar.decided_at DESC NULLS LAST, ar.requested_at DESC, ar.id DESC
                ) AS admission_rank
            FROM admission_requests ar
            JOIN admissions a
                ON a.clinic_id = ar.clinic_id
               AND a.patient_id = ar.patient_id
               AND a.status = 'ACTIVE'
            LEFT JOIN admission_requests linked
                ON linked.clinic_id = a.clinic_id
               AND linked.admission_id = a.id
               AND linked.id <> ar.id
            WHERE ar.status = 'APPROVED'
              AND ar.admission_id IS NULL
              AND linked.id IS NULL
        )
        UPDATE admission_requests ar
        SET admission_id = c.admission_id
        FROM candidate_links c
        WHERE ar.id = c.request_id
          AND c.request_rank = 1
          AND c.request_candidate_count = 1
          AND c.admission_rank = 1;
        """
    )


def downgrade() -> None:
    # Data backfill is intentionally non-reversible.
    pass
