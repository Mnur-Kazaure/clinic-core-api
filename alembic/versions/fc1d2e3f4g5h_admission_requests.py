"""add admission requests workflow

Revision ID: fc1d2e3f4g5h
Revises: fb1c2d3e4f5g
Create Date: 2026-02-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "fc1d2e3f4g5h"
down_revision = "fb1c2d3e4f5g"
branch_labels = None
depends_on = None


def upgrade() -> None:
    admission_request_status = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "REJECTED",
        "CANCELLED",
        name="admission_request_status",
        create_type=False,
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        admission_request_status.create(bind, checkfirst=True)

    op.create_table(
        "admission_requests",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column(
            "admission_type",
            postgresql.ENUM(
                "EMERGENCY",
                "ELECTIVE",
                name="admission_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            admission_request_status,
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.String(length=500), nullable=True),
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
        sa.UniqueConstraint("id", "clinic_id", name="uq_admission_requests_id_clinic"),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_admission_requests_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_admission_requests_clinic_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("length(reason) >= 3", name="ck_admission_requests_reason_length"),
    )

    op.create_index(
        "ix_admission_requests_clinic_status_requested_at",
        "admission_requests",
        ["clinic_id", "status", "requested_at"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_admission_requests_pending_patient",
            "admission_requests",
            ["clinic_id", "patient_id"],
            unique=True,
            postgresql_where=sa.text("status = 'PENDING'"),
        )
    else:
        op.create_index(
            "ix_admission_requests_patient_status",
            "admission_requests",
            ["clinic_id", "patient_id", "status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_admission_requests_pending_patient", table_name="admission_requests")
    else:
        op.drop_index("ix_admission_requests_patient_status", table_name="admission_requests")

    op.drop_index(
        "ix_admission_requests_clinic_status_requested_at",
        table_name="admission_requests",
    )
    op.drop_table("admission_requests")
    op.execute("DROP TYPE IF EXISTS admission_request_status")
