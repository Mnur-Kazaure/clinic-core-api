"""phase2 admissions beds transfers

Revision ID: e2f3a4b5c6d7
Revises: 765723687708
Create Date: 2026-01-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "765723687708"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)

    if dialect == "postgresql":
        admission_type = postgresql.ENUM(
            "EMERGENCY",
            "ELECTIVE",
            name="admission_type",
            create_type=False,
        )
        admission_status = postgresql.ENUM(
            "ACTIVE",
            "DISCHARGED",
            "CANCELLED",
            name="admission_status",
            create_type=False,
        )
        ward_type = postgresql.ENUM(
            "GENERAL",
            "ICU",
            "MATERNITY",
            "PEDIATRIC",
            "EMERGENCY",
            "ISOLATION",
            name="ward_type",
            create_type=False,
        )
        bed_status = postgresql.ENUM(
            "AVAILABLE",
            "OUT_OF_SERVICE",
            name="bed_status",
            create_type=False,
        )
        bed_assignment_type = postgresql.ENUM(
            "ASSIGN",
            "TRANSFER",
            name="bed_assignment_type",
            create_type=False,
        )
        admission_type.create(bind, checkfirst=True)
        admission_status.create(bind, checkfirst=True)
        ward_type.create(bind, checkfirst=True)
        bed_status.create(bind, checkfirst=True)
        bed_assignment_type.create(bind, checkfirst=True)
    else:
        admission_type = sa.Enum(
            "EMERGENCY",
            "ELECTIVE",
            name="admission_type",
        )
        admission_status = sa.Enum(
            "ACTIVE",
            "DISCHARGED",
            "CANCELLED",
            name="admission_status",
        )
        ward_type = sa.Enum(
            "GENERAL",
            "ICU",
            "MATERNITY",
            "PEDIATRIC",
            "EMERGENCY",
            "ISOLATION",
            name="ward_type",
        )
        bed_status = sa.Enum(
            "AVAILABLE",
            "OUT_OF_SERVICE",
            name="bed_status",
        )
        bed_assignment_type = sa.Enum(
            "ASSIGN",
            "TRANSFER",
            name="bed_assignment_type",
        )

    if dialect != "sqlite":
        existing_uq = {
            uq["name"] for uq in inspector.get_unique_constraints("patients")
        }
        if "uq_patients_id_clinic" not in existing_uq:
            op.create_unique_constraint(
                "uq_patients_id_clinic",
                "patients",
                ["id", "clinic_id"],
            )
        existing_uq = {
            uq["name"] for uq in inspector.get_unique_constraints("visits")
        }
        if "uq_visits_id_clinic" not in existing_uq:
            op.create_unique_constraint(
                "uq_visits_id_clinic",
                "visits",
                ["id", "clinic_id"],
            )

    op.create_table(
        "admissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("admission_type", admission_type, nullable=False),
        sa.Column("status", admission_status, nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("discharged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("id", "clinic_id", name="uq_admissions_id_clinic"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_admissions_clinic_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_admissions_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "(status != 'DISCHARGED') OR (discharged_at IS NOT NULL)",
            name="ck_admissions_discharged_at",
        ),
        sa.CheckConstraint(
            "(status != 'CANCELLED') OR (cancelled_at IS NOT NULL AND cancel_reason IS NOT NULL)",
            name="ck_admissions_cancelled_at_reason",
        ),
        sa.CheckConstraint(
            "(status != 'ACTIVE') OR (discharged_at IS NULL AND cancelled_at IS NULL)",
            name="ck_admissions_active_no_end",
        ),
    )

    op.create_table(
        "wards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("ward_type", ward_type, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("id", "clinic_id", name="uq_wards_id_clinic"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_wards_clinic_id",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "beds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("ward_id", sa.Uuid(), nullable=False),
        sa.Column("bed_label", sa.String(length=100), nullable=False),
        sa.Column("status", bed_status, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("id", "clinic_id", name="uq_beds_id_clinic"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_beds_clinic_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ward_id", "clinic_id"],
            ["wards.id", "wards.clinic_id"],
            name="fk_beds_ward_clinic",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "bed_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("bed_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=False),
        sa.Column("assignment_type", bed_assignment_type, nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_bed_assignments_admission_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["bed_id", "clinic_id"],
            ["beds.id", "beds.clinic_id"],
            name="fk_bed_assignments_bed_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
            name="fk_bed_assignments_assigned_by",
        ),
        sa.CheckConstraint(
            "(assignment_type != 'TRANSFER') OR (reason IS NOT NULL AND length(reason) >= 3)",
            name="ck_bed_assignment_transfer_reason",
        ),
    )

    op.create_table(
        "admission_visit_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("visit_id", "clinic_id", name="uq_admission_visit_links_visit_clinic"),
        sa.ForeignKeyConstraint(
            ["admission_id", "clinic_id"],
            ["admissions.id", "admissions.clinic_id"],
            name="fk_admission_visit_links_admission_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_admission_visit_links_visit_clinic",
            ondelete="CASCADE",
        ),
    )

    # Add break_glass flag to access_logs
    op.add_column(
        "access_logs",
        sa.Column("break_glass", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    if dialect != "sqlite":
        op.create_index(
            "uq_bed_assignments_active_bed",
            "bed_assignments",
            ["bed_id"],
            unique=True,
            postgresql_where=sa.text("released_at IS NULL"),
        )
        op.create_index(
            "uq_bed_assignments_active_admission",
            "bed_assignments",
            ["admission_id"],
            unique=True,
            postgresql_where=sa.text("released_at IS NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != "sqlite":
        op.drop_index("uq_bed_assignments_active_admission", table_name="bed_assignments")
        op.drop_index("uq_bed_assignments_active_bed", table_name="bed_assignments")

    op.drop_column("access_logs", "break_glass")

    op.drop_table("admission_visit_links")
    op.drop_table("bed_assignments")
    op.drop_table("beds")
    op.drop_table("wards")
    op.drop_table("admissions")

    if dialect != "sqlite":
        op.execute("DROP TYPE IF EXISTS bed_assignment_type")
        op.execute("DROP TYPE IF EXISTS bed_status")
        op.execute("DROP TYPE IF EXISTS ward_type")
        op.execute("DROP TYPE IF EXISTS admission_status")
        op.execute("DROP TYPE IF EXISTS admission_type")
