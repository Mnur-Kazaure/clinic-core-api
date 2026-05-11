"""allow operational updates on signed prescriptions

Revision ID: b2c3d4e5f6a
Revises: a1b2c3d4e5f6
Create Date: 2026-03-24 16:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prescriptions_block_update_signed()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.record_status = 'VOIDED' THEN
                RAISE EXCEPTION 'signed record immutable';
            END IF;

            IF OLD.record_status = 'SIGNED' THEN
                IF NEW.record_status NOT IN ('SIGNED', 'VOIDED') THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;

                IF NEW.record_status = 'VOIDED' AND (
                    NEW.void_reason IS NULL OR
                    NEW.status <> 'CANCELLED' OR
                    NEW.cancelled_at IS NULL
                ) THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;

                IF
                    NEW.consultation_id IS DISTINCT FROM OLD.consultation_id OR
                    NEW.visit_id IS DISTINCT FROM OLD.visit_id OR
                    NEW.clinic_id IS DISTINCT FROM OLD.clinic_id OR
                    NEW.prescribed_by IS DISTINCT FROM OLD.prescribed_by OR
                    NEW.drug_name IS DISTINCT FROM OLD.drug_name OR
                    NEW.dosage IS DISTINCT FROM OLD.dosage OR
                    NEW.frequency IS DISTINCT FROM OLD.frequency OR
                    NEW.duration IS DISTINCT FROM OLD.duration OR
                    NEW.instructions IS DISTINCT FROM OLD.instructions OR
                    NEW.issued_at IS DISTINCT FROM OLD.issued_at OR
                    NEW.signed_at IS DISTINCT FROM OLD.signed_at
                THEN
                    RAISE EXCEPTION 'signed record immutable';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
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
