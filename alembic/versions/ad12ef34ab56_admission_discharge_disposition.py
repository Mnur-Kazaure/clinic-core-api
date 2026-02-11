"""admission discharge disposition

Revision ID: ad12ef34ab56
Revises: 95b89aac78da
Create Date: 2026-02-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ad12ef34ab56"
down_revision: Union[str, Sequence[str], None] = "95b89aac78da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DISCHARGE_DISPOSITIONS = (
    "HOME",
    "TRANSFERRED_OUT",
    "DECEASED",
    "LAMA",
    "ELOPED",
    "OTHER",
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != "sqlite":
        # Create type idempotently to avoid DuplicateObject on existing DBs.
        from sqlalchemy.dialects import postgresql

        disposition_enum = postgresql.ENUM(
            *DISCHARGE_DISPOSITIONS,
            name="admission_discharge_disposition",
            create_type=False,
        )
        disposition_enum.create(bind, checkfirst=True)
    else:
        disposition_enum = sa.Enum(
            *DISCHARGE_DISPOSITIONS,
            name="admission_discharge_disposition",
        )

    with op.batch_alter_table("admissions") as batch:
        batch.add_column(
            sa.Column(
                "discharge_disposition",
                disposition_enum,
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "transferred_to_facility",
                sa.String(length=200),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "death_pronounced_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "discharge_notes",
                sa.String(length=500),
                nullable=True,
            )
        )

    # Backfill legacy discharged rows so new checks are safe on existing DBs.
    op.execute(
        "UPDATE admissions "
        "SET discharge_disposition = 'HOME' "
        "WHERE status = 'DISCHARGED' AND discharge_disposition IS NULL"
    )

    with op.batch_alter_table("admissions") as batch:
        batch.create_check_constraint(
            "ck_admissions_discharge_disposition_required",
            "(status != 'DISCHARGED') OR (discharge_disposition IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_admissions_discharged_not_cancelled",
            "(status != 'DISCHARGED') OR (cancelled_at IS NULL AND cancel_reason IS NULL)",
        )
        batch.create_check_constraint(
            "ck_admissions_cancelled_not_discharged",
            "(status != 'CANCELLED') OR (discharged_at IS NULL AND discharge_disposition IS NULL)",
        )
        batch.create_check_constraint(
            "ck_admissions_transfer_requires_facility",
            "(discharge_disposition != 'TRANSFERRED_OUT') OR (transferred_to_facility IS NOT NULL AND length(transferred_to_facility) >= 3)",
        )
        batch.create_check_constraint(
            "ck_admissions_transfer_no_death_time",
            "(discharge_disposition != 'TRANSFERRED_OUT') OR (death_pronounced_at IS NULL)",
        )
        batch.create_check_constraint(
            "ck_admissions_death_requires_time",
            "(discharge_disposition != 'DECEASED') OR (death_pronounced_at IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_admissions_death_no_transfer_facility",
            "(discharge_disposition != 'DECEASED') OR (transferred_to_facility IS NULL)",
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table("admissions") as batch:
        batch.drop_constraint("ck_admissions_death_no_transfer_facility", type_="check")
        batch.drop_constraint("ck_admissions_death_requires_time", type_="check")
        batch.drop_constraint("ck_admissions_transfer_no_death_time", type_="check")
        batch.drop_constraint("ck_admissions_transfer_requires_facility", type_="check")
        batch.drop_constraint("ck_admissions_cancelled_not_discharged", type_="check")
        batch.drop_constraint("ck_admissions_discharged_not_cancelled", type_="check")
        batch.drop_constraint("ck_admissions_discharge_disposition_required", type_="check")

        batch.drop_column("discharge_notes")
        batch.drop_column("death_pronounced_at")
        batch.drop_column("transferred_to_facility")
        batch.drop_column("discharge_disposition")

    if dialect != "sqlite":
        op.execute("DROP TYPE IF EXISTS admission_discharge_disposition")

