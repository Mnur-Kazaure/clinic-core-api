"""add prescription fulfillment events

Revision ID: cce96ad7bb91
Revises: 2c0d54e1275a
Create Date: 2026-02-05 18:05:15.981300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cce96ad7bb91'
down_revision: Union[str, Sequence[str], None] = '2c0d54e1275a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    fulfillment_type = sa.Enum(
        "DISPENSED_IN_HOUSE",
        "DISPENSED_EXTERNAL",
        name="prescription_fulfillment_type",
    )

    op.create_table(
        "prescription_fulfillment_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("prescription_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("fulfillment_type", fulfillment_type, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_prescription_fulfillment_events_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_prescription_fulfillment_events_actor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prescription_id", "clinic_id"],
            ["prescriptions.id", "prescriptions.clinic_id"],
            name="fk_prescription_fulfillment_events_prescription_clinic",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "clinic_id",
            "prescription_id",
            name="uq_prescription_fulfillment_events_prescription",
        ),
        sa.CheckConstraint(
            "(quantity IS NULL) OR (quantity > 0)",
            name="ck_prescription_fulfillment_quantity_positive",
        ),
    )

    # Append-only enforcement
    if dialect == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION prescription_fulfillment_events_block_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'prescription_fulfillment_events are append-only';
END;
$$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
CREATE TRIGGER prescription_fulfillment_events_block_mutation
BEFORE UPDATE OR DELETE ON prescription_fulfillment_events
FOR EACH ROW EXECUTE FUNCTION prescription_fulfillment_events_block_mutation();
            """
        )
    else:
        op.execute(
            """
CREATE TRIGGER prescription_fulfillment_events_block_update
BEFORE UPDATE ON prescription_fulfillment_events
BEGIN
    SELECT RAISE(FAIL, 'prescription_fulfillment_events are append-only');
END;
            """
        )
        op.execute(
            """
CREATE TRIGGER prescription_fulfillment_events_block_delete
BEFORE DELETE ON prescription_fulfillment_events
BEGIN
    SELECT RAISE(FAIL, 'prescription_fulfillment_events are append-only');
END;
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS prescription_fulfillment_events_block_mutation ON prescription_fulfillment_events"
        )
        op.execute("DROP FUNCTION IF EXISTS prescription_fulfillment_events_block_mutation")
    else:
        op.execute("DROP TRIGGER IF EXISTS prescription_fulfillment_events_block_update")
        op.execute("DROP TRIGGER IF EXISTS prescription_fulfillment_events_block_delete")

    op.drop_table("prescription_fulfillment_events")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS prescription_fulfillment_type")
