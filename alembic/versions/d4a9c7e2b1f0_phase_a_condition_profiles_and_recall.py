"""phase A condition profiles, diagnosis mapping, and chronic recalls

Revision ID: d4a9c7e2b1f0
Revises: c1d2e3f4g5h6, fc1d2e3f4g5h
Create Date: 2026-02-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4a9c7e2b1f0"
down_revision = ("c1d2e3f4g5h6", "fc1d2e3f4g5h")
branch_labels = None
depends_on = None


def _create_enum_if_needed(bind, enum_type: sa.Enum) -> None:
    if bind.dialect.name == "postgresql":
        enum_type.create(bind, checkfirst=True)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        recall_interval_unit = postgresql.ENUM(
            "DAYS",
            "WEEKS",
            "MONTHS",
            name="recall_interval_unit",
            create_type=False,
        )
        follow_up_priority = postgresql.ENUM(
            "ROUTINE",
            "IMPORTANT",
            "CRITICAL",
            name="follow_up_priority",
            create_type=False,
        )
        diagnosis_system = postgresql.ENUM(
            "ICD10",
            "ICPC2",
            "LOCAL",
            name="diagnosis_system",
            create_type=False,
        )
        diagnosis_mapping_confidence = postgresql.ENUM(
            "HIGH",
            "MEDIUM",
            name="diagnosis_mapping_confidence",
            create_type=False,
        )
    else:
        recall_interval_unit = sa.Enum(
            "DAYS",
            "WEEKS",
            "MONTHS",
            name="recall_interval_unit",
        )
        follow_up_priority = sa.Enum(
            "ROUTINE",
            "IMPORTANT",
            "CRITICAL",
            name="follow_up_priority",
        )
        diagnosis_system = sa.Enum(
            "ICD10",
            "ICPC2",
            "LOCAL",
            name="diagnosis_system",
        )
        diagnosis_mapping_confidence = sa.Enum(
            "HIGH",
            "MEDIUM",
            name="diagnosis_mapping_confidence",
        )

    _create_enum_if_needed(bind, recall_interval_unit)
    _create_enum_if_needed(bind, follow_up_priority)
    _create_enum_if_needed(bind, diagnosis_system)
    _create_enum_if_needed(bind, diagnosis_mapping_confidence)

    op.create_table(
        "condition_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column(
            "recall_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("default_interval_value", sa.Integer(), nullable=False),
        sa.Column("default_interval_unit", recall_interval_unit, nullable=False),
        sa.Column(
            "default_priority",
            follow_up_priority,
            nullable=False,
            server_default="IMPORTANT",
        ),
        sa.Column(
            "cooldown_days",
            sa.Integer(),
            nullable=False,
            server_default="90",
        ),
        sa.Column("keyword_synonyms", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "clinic_id", name="uq_condition_profiles_id_clinic"),
        sa.UniqueConstraint("clinic_id", "code", name="uq_condition_profiles_clinic_code"),
        sa.UniqueConstraint(
            "clinic_id",
            "display_name",
            name="uq_condition_profiles_clinic_display_name",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_condition_profiles_clinic_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_condition_profiles_created_by",
        ),
    )
    op.create_index(
        "ix_condition_profiles_clinic_recall_enabled",
        "condition_profiles",
        ["clinic_id", "recall_enabled"],
    )

    op.create_table(
        "diagnosis_condition_map",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("diagnosis_system", diagnosis_system, nullable=False),
        sa.Column("diagnosis_code", sa.String(length=64), nullable=False),
        sa.Column("condition_profile_id", sa.UUID(), nullable=False),
        sa.Column(
            "confidence",
            diagnosis_mapping_confidence,
            nullable=False,
            server_default="HIGH",
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_diagnosis_condition_map_clinic_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["condition_profile_id", "clinic_id"],
            ["condition_profiles.id", "condition_profiles.clinic_id"],
            name="fk_diagnosis_condition_map_condition_profile_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_diagnosis_condition_map_created_by",
        ),
    )
    op.create_index(
        "ix_diagnosis_condition_map_clinic_lookup",
        "diagnosis_condition_map",
        ["clinic_id", "diagnosis_system", "diagnosis_code"],
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_diagnosis_condition_map_active",
            "diagnosis_condition_map",
            ["clinic_id", "diagnosis_system", "diagnosis_code"],
            unique=True,
            postgresql_where=sa.text("active = true"),
        )
    else:
        op.create_index(
            "uq_diagnosis_condition_map_active",
            "diagnosis_condition_map",
            ["clinic_id", "diagnosis_system", "diagnosis_code"],
            unique=True,
            sqlite_where=sa.text("active = 1"),
        )

    op.create_table(
        "chronic_recalls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id_canonical", sa.UUID(), nullable=False),
        sa.Column("condition_profile_id", sa.UUID(), nullable=False),
        sa.Column("assigned_clinician_id", sa.UUID(), nullable=False),
        sa.Column("interval_value", sa.Integer(), nullable=False),
        sa.Column("interval_unit", recall_interval_unit, nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "generation_paused",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("last_generated_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_reason", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_chronic_recalls_clinic_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id_canonical", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_chronic_recalls_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["condition_profile_id", "clinic_id"],
            ["condition_profiles.id", "condition_profiles.clinic_id"],
            name="fk_chronic_recalls_condition_profile_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_clinician_id"],
            ["users.id"],
            name="fk_chronic_recalls_assigned_clinician",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_chronic_recalls_created_by",
        ),
    )
    op.create_index(
        "ix_chronic_recalls_clinic_active_due",
        "chronic_recalls",
        ["clinic_id", "active", "next_due_at"],
    )
    op.create_index(
        "ix_chronic_recalls_patient_active",
        "chronic_recalls",
        ["clinic_id", "patient_id_canonical", "active"],
    )
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_chronic_recalls_active_patient_condition",
            "chronic_recalls",
            ["clinic_id", "patient_id_canonical", "condition_profile_id"],
            unique=True,
            postgresql_where=sa.text("active = true"),
        )
    else:
        op.create_index(
            "uq_chronic_recalls_active_patient_condition",
            "chronic_recalls",
            ["clinic_id", "patient_id_canonical", "condition_profile_id"],
            unique=True,
            sqlite_where=sa.text("active = 1"),
        )


def downgrade() -> None:
    op.drop_index(
        "uq_chronic_recalls_active_patient_condition",
        table_name="chronic_recalls",
    )
    op.drop_index("ix_chronic_recalls_patient_active", table_name="chronic_recalls")
    op.drop_index("ix_chronic_recalls_clinic_active_due", table_name="chronic_recalls")
    op.drop_table("chronic_recalls")

    op.drop_index("uq_diagnosis_condition_map_active", table_name="diagnosis_condition_map")
    op.drop_index(
        "ix_diagnosis_condition_map_clinic_lookup",
        table_name="diagnosis_condition_map",
    )
    op.drop_table("diagnosis_condition_map")

    op.drop_index(
        "ix_condition_profiles_clinic_recall_enabled",
        table_name="condition_profiles",
    )
    op.drop_table("condition_profiles")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS diagnosis_mapping_confidence")
        op.execute("DROP TYPE IF EXISTS diagnosis_system")
        op.execute("DROP TYPE IF EXISTS follow_up_priority")
        op.execute("DROP TYPE IF EXISTS recall_interval_unit")
