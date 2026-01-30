"""enforce merged patients require identity mapping

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-01-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MERGE_CHECK_SQL = """
SELECT 1
FROM patient_identity_map pim
WHERE pim.clinic_id = NEW.clinic_id
  AND pim.from_patient_id = NEW.id
  AND NOT EXISTS (
      SELECT 1
      FROM identity_map_revocations rev
      WHERE rev.clinic_id = pim.clinic_id
        AND rev.map_id = pim.id
  )
"""


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION patients_require_merge_mapping()
RETURNS trigger AS $$
BEGIN
    IF NEW.identity_state = 'MERGED' THEN
        IF NOT EXISTS ("""
            + MERGE_CHECK_SQL
            + """
        ) THEN
            RAISE EXCEPTION 'merged patient requires identity mapping';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
CREATE TRIGGER patients_require_merge_mapping
BEFORE INSERT OR UPDATE ON patients
FOR EACH ROW
EXECUTE FUNCTION patients_require_merge_mapping();
            """
        )
    else:
        # SQLite fallback triggers
        op.execute(
            """
CREATE TRIGGER patients_require_merge_mapping_insert
BEFORE INSERT ON patients
WHEN NEW.identity_state = 'MERGED'
BEGIN
    SELECT CASE
        WHEN NOT EXISTS ("""
            + MERGE_CHECK_SQL
            + """
        ) THEN
            RAISE(FAIL, 'merged patient requires identity mapping')
    END;
END;
            """
        )
        op.execute(
            """
CREATE TRIGGER patients_require_merge_mapping_update
BEFORE UPDATE ON patients
WHEN NEW.identity_state = 'MERGED'
BEGIN
    SELECT CASE
        WHEN NOT EXISTS ("""
            + MERGE_CHECK_SQL
            + """
        ) THEN
            RAISE(FAIL, 'merged patient requires identity mapping')
    END;
END;
            """
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS patients_require_merge_mapping ON patients")
        op.execute("DROP FUNCTION IF EXISTS patients_require_merge_mapping")
    else:
        op.execute("DROP TRIGGER IF EXISTS patients_require_merge_mapping_insert")
        op.execute("DROP TRIGGER IF EXISTS patients_require_merge_mapping_update")
