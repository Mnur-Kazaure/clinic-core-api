"""phase C visit linked follow-up field

Revision ID: c8e1f9a2b3d4
Revises: f4c8b2d1a6e9
Create Date: 2026-02-16 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8e1f9a2b3d4"
down_revision = "f4c8b2d1a6e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visits", sa.Column("linked_follow_up_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_visits_linked_follow_up_id",
        "visits",
        "follow_ups",
        ["linked_follow_up_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_visits_linked_follow_up_id",
        "visits",
        ["linked_follow_up_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_visits_linked_follow_up_id", table_name="visits")
    op.drop_constraint("fk_visits_linked_follow_up_id", "visits", type_="foreignkey")
    op.drop_column("visits", "linked_follow_up_id")
