"""anc pregnancy episodes

Revision ID: d423f3c6249b
Revises: 43dad626f6b7
Create Date: 2026-02-08 13:44:52.596286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


EPISODE_STATUSES = ("ACTIVE", "CLOSED")


# revision identifiers, used by Alembic.
revision: str = 'd423f3c6249b'
down_revision: Union[str, Sequence[str], None] = '43dad626f6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        episode_status_enum = postgresql.ENUM(
            *EPISODE_STATUSES,
            name="pregnancy_episode_status",
            create_type=False,
        )
        episode_status_enum.create(bind, checkfirst=True)
    else:
        episode_status_enum = sa.Enum(
            *EPISODE_STATUSES,
            name="pregnancy_episode_status",
        )

    op.create_table(
        "pregnancy_episodes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            episode_status_enum,
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("lmp_date", sa.Date(), nullable=True),
        sa.Column("edd_date", sa.Date(), nullable=True),
        sa.Column("gravida", sa.Integer(), nullable=True),
        sa.Column("parity", sa.Integer(), nullable=True),
        sa.Column("booking_reg_no", sa.Text(), nullable=True),
        sa.Column("past_medical_history", sa.Text(), nullable=True),
        sa.Column("past_surgical_history", sa.Text(), nullable=True),
        sa.Column("history_present_pregnancy", sa.Text(), nullable=True),
        sa.Column("general_exam", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_pregnancy_episodes_clinic", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_pregnancy_episodes_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_pregnancy_episodes_created_by",
        ),
        sa.UniqueConstraint("id", "clinic_id", name="uq_pregnancy_episodes_id_clinic"),
    )

    # One ACTIVE episode per patient per clinic.
    op.create_index(
        "uq_pregnancy_episodes_active_per_patient",
        "pregnancy_episodes",
        ["clinic_id", "patient_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.drop_index("uq_pregnancy_episodes_active_per_patient", table_name="pregnancy_episodes")
    op.drop_table("pregnancy_episodes")

    if dialect != "sqlite":
        from sqlalchemy.dialects import postgresql

        episode_status_enum = postgresql.ENUM(
            *EPISODE_STATUSES,
            name="pregnancy_episode_status",
            create_type=False,
        )
        episode_status_enum.drop(bind, checkfirst=True)
