"""fix anc maternity timestamp drift

Revision ID: 4d1f2a8c9b7e
Revises: 3c2f9a7b1e4d
Create Date: 2026-02-10 00:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d1f2a8c9b7e"
down_revision: Union[str, Sequence[str], None] = "3c2f9a7b1e4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


def _add_timestamp_column(table: str, column: str) -> None:
    op.add_column(
        table,
        sa.Column(
            column,
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in (
        "anc_encounters",
        "maternity_delivery_records",
        "maternity_postnatal_notes",
        "family_planning_events",
    ):
        if not _has_column(inspector, table_name, "created_at"):
            _add_timestamp_column(table_name, "created_at")
        if not _has_column(inspector, table_name, "updated_at"):
            _add_timestamp_column(table_name, "updated_at")

    # Align column names with ORM model/service usage.
    if _has_column(inspector, "pregnancy_previous_pregnancies", "added_by") and not _has_column(
        inspector, "pregnancy_previous_pregnancies", "created_by"
    ):
        op.alter_column(
            "pregnancy_previous_pregnancies",
            "added_by",
            new_column_name="created_by",
            existing_type=sa.Uuid(),
            existing_nullable=False,
        )

    if _has_column(inspector, "pregnancy_previous_pregnancies", "added_at") and not _has_column(
        inspector, "pregnancy_previous_pregnancies", "created_at"
    ):
        op.alter_column(
            "pregnancy_previous_pregnancies",
            "added_at",
            new_column_name="created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )

    inspector = sa.inspect(bind)
    if not _has_column(inspector, "pregnancy_previous_pregnancies", "updated_at"):
        _add_timestamp_column("pregnancy_previous_pregnancies", "updated_at")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    for table_name in (
        "anc_encounters",
        "maternity_delivery_records",
        "maternity_postnatal_notes",
        "family_planning_events",
        "pregnancy_previous_pregnancies",
    ):
        inspector = sa.inspect(bind)
        if _has_column(inspector, table_name, "updated_at"):
            op.drop_column(table_name, "updated_at")
        inspector = sa.inspect(bind)
        if table_name != "pregnancy_previous_pregnancies" and _has_column(
            inspector, table_name, "created_at"
        ):
            op.drop_column(table_name, "created_at")

    inspector = sa.inspect(bind)
    if _has_column(inspector, "pregnancy_previous_pregnancies", "created_at") and not _has_column(
        inspector, "pregnancy_previous_pregnancies", "added_at"
    ):
        op.alter_column(
            "pregnancy_previous_pregnancies",
            "created_at",
            new_column_name="added_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )

    inspector = sa.inspect(bind)
    if _has_column(inspector, "pregnancy_previous_pregnancies", "created_by") and not _has_column(
        inspector, "pregnancy_previous_pregnancies", "added_by"
    ):
        op.alter_column(
            "pregnancy_previous_pregnancies",
            "created_by",
            new_column_name="added_by",
            existing_type=sa.Uuid(),
            existing_nullable=False,
        )
