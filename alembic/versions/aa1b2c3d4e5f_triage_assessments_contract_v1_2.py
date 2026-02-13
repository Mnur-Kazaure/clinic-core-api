"""triage assessments contract v1.2

Revision ID: aa1b2c3d4e5f
Revises: 8b2c3d4e5f6a
Create Date: 2026-02-13 00:00:00.000000
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "aa1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "8b2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _build_enum(name: str, values: tuple[str, ...], bind) -> sa.Enum:
    if bind.dialect.name == "postgresql":
        enum = postgresql.ENUM(*values, name=name, create_type=False)
        enum.create(bind, checkfirst=True)
        return enum
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "triage_assessments" in inspector.get_table_names():
        return

    triage_scale_enum = _build_enum(
        "triage_scale_version",
        ("PHC_V1",),
        bind,
    )
    complaint_severity_enum = _build_enum(
        "triage_complaint_severity",
        ("MILD", "MODERATE", "SEVERE"),
        bind,
    )
    missing_vitals_enum = _build_enum(
        "triage_missing_vital_reason_code",
        ("DEVICE_UNAVAILABLE", "PATIENT_UNSTABLE", "CLINICAL_JUDGMENT", "REFUSED"),
        bind,
    )
    fallback_reason_enum = _build_enum(
        "triage_fallback_reason_code",
        ("NO_TRIAGER_ON_DUTY", "MASS_CASUALTY", "EMERGENCY_OVERRIDE", "OTHER"),
        bind,
    )
    finalize_action_enum = _build_enum(
        "triage_finalize_action",
        ("QUEUE_FOR_CONSULTATION", "REFER_OUT_IMMEDIATE"),
        bind,
    )

    # Reuse existing clinical_priority_level enum for acuity_level.
    if bind.dialect.name == "postgresql":
        acuity_enum = postgresql.ENUM(
            "CRITICAL",
            "URGENT",
            "ROUTINE",
            name="clinical_priority_level",
            create_type=False,
        )
        acuity_enum.create(bind, checkfirst=True)
    else:
        acuity_enum = sa.Enum(
            "CRITICAL",
            "URGENT",
            "ROUTINE",
            name="clinical_priority_level",
        )

    op.create_table(
        "triage_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("assessed_by", sa.Uuid(), nullable=False),
        sa.Column("assessed_by_role", sa.String(length=50), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_by", sa.Uuid(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "triage_scale_version",
            triage_scale_enum,
            nullable=False,
            server_default="PHC_V1",
        ),
        sa.Column("acuity_level", acuity_enum, nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=False),
        sa.Column("complaint_severity", complaint_severity_enum, nullable=False),
        sa.Column("triage_note", sa.Text(), nullable=True),
        sa.Column("danger_sign_codes", sa.JSON(), nullable=True),
        sa.Column("temp_c", sa.Numeric(5, 2), nullable=True),
        sa.Column("pulse_bpm", sa.Integer(), nullable=True),
        sa.Column("rr_bpm", sa.Integer(), nullable=True),
        sa.Column("sbp_mmhg", sa.Integer(), nullable=True),
        sa.Column("dbp_mmhg", sa.Integer(), nullable=True),
        sa.Column("spo2_pct", sa.Integer(), nullable=True),
        sa.Column("missing_vitals_reason_code", missing_vitals_enum, nullable=True),
        sa.Column(
            "is_doctor_fallback",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("fallback_reason_code", fallback_reason_enum, nullable=True),
        sa.Column("fallback_reason_text", sa.Text(), nullable=True),
        sa.Column(
            "triage_finalize_action",
            finalize_action_enum,
            nullable=False,
            server_default="QUEUE_FOR_CONSULTATION",
        ),
        sa.Column("referred_facility", sa.String(length=200), nullable=True),
        sa.Column("referral_reason", sa.Text(), nullable=True),
        sa.Column("supersedes_assessment_id", sa.Uuid(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correction_reason_code", sa.String(length=50), nullable=True),
        sa.Column("correction_reason_text", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
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
            ["visit_id", "clinic_id"],
            ["visits.id", "visits.clinic_id"],
            name="fk_triage_assessment_visit_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_triage_assessment_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_triage_assessment_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assessed_by"],
            ["users.id"],
            name="fk_triage_assessment_assessed_by",
        ),
        sa.ForeignKeyConstraint(
            ["finalized_by"],
            ["users.id"],
            name="fk_triage_assessment_finalized_by",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_assessment_id"],
            ["triage_assessments.id"],
            name="fk_triage_assessment_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(superseded_at IS NULL) OR (supersedes_assessment_id IS NOT NULL)",
            name="ck_triage_supersede_linked",
        ),
        sa.CheckConstraint(
            "(is_doctor_fallback = false) OR (fallback_reason_code IS NOT NULL)",
            name="ck_triage_fallback_reason_required",
        ),
        sa.CheckConstraint(
            "(fallback_reason_code IS NULL OR fallback_reason_code != 'OTHER') OR "
            "(fallback_reason_text IS NOT NULL AND length(trim(fallback_reason_text)) >= 15)",
            name="ck_triage_fallback_other_reason_text",
        ),
        sa.CheckConstraint(
            "(triage_finalize_action != 'REFER_OUT_IMMEDIATE') OR "
            "(referred_facility IS NOT NULL AND length(trim(referred_facility)) >= 3)",
            name="ck_triage_referral_facility_required",
        ),
        sa.CheckConstraint(
            "(triage_finalize_action != 'REFER_OUT_IMMEDIATE') OR "
            "(referral_reason IS NOT NULL AND length(trim(referral_reason)) >= 3)",
            name="ck_triage_referral_reason_required",
        ),
        sa.CheckConstraint(
            "(acuity_level != 'CRITICAL') OR "
            "(triage_note IS NOT NULL AND length(trim(triage_note)) >= 5)",
            name="ck_triage_critical_note_required",
        ),
        sa.CheckConstraint(
            "(temp_c IS NULL OR (temp_c >= 25 AND temp_c <= 46))",
            name="ck_triage_temp_sane",
        ),
        sa.CheckConstraint(
            "(pulse_bpm IS NULL OR (pulse_bpm >= 20 AND pulse_bpm <= 260))",
            name="ck_triage_pulse_sane",
        ),
        sa.CheckConstraint(
            "(rr_bpm IS NULL OR (rr_bpm >= 5 AND rr_bpm <= 80))",
            name="ck_triage_rr_sane",
        ),
        sa.CheckConstraint(
            "(sbp_mmhg IS NULL OR (sbp_mmhg >= 50 AND sbp_mmhg <= 300))",
            name="ck_triage_sbp_sane",
        ),
        sa.CheckConstraint(
            "(dbp_mmhg IS NULL OR (dbp_mmhg >= 30 AND dbp_mmhg <= 200))",
            name="ck_triage_dbp_sane",
        ),
        sa.CheckConstraint(
            "(spo2_pct IS NULL OR (spo2_pct >= 30 AND spo2_pct <= 100))",
            name="ck_triage_spo2_sane",
        ),
        sa.CheckConstraint(
            "(temp_c IS NOT NULL AND pulse_bpm IS NOT NULL AND rr_bpm IS NOT NULL "
            "AND sbp_mmhg IS NOT NULL AND dbp_mmhg IS NOT NULL) "
            "OR (missing_vitals_reason_code IS NOT NULL)",
            name="ck_triage_missing_vitals_reason",
        ),
    )

    if bind.dialect.name == "postgresql":
        op.create_index(
            "ix_triage_assessments_visit_active",
            "triage_assessments",
            ["visit_id"],
            unique=True,
            postgresql_where=sa.text("superseded_at IS NULL"),
        )
    else:
        op.create_index(
            "ix_triage_assessments_visit_active",
            "triage_assessments",
            ["visit_id"],
            unique=False,
        )

    op.create_index("ix_triage_assessments_clinic", "triage_assessments", ["clinic_id"])
    op.create_index("ix_triage_assessments_patient", "triage_assessments", ["patient_id"])
    op.create_index(
        "ix_triage_assessments_visit_assessed_at",
        "triage_assessments",
        ["visit_id", "assessed_at"],
    )

    # Backfill historical visits that already progressed beyond TRIAGED.
    # Active TRIAGED visits are intentionally excluded and must be re-triaged.
    backfill_rows = bind.execute(
        sa.text(
            """
            WITH first_triage AS (
                SELECT
                    h.visit_id,
                    h.changed_by,
                    h.created_at,
                    row_number() OVER (
                        PARTITION BY h.visit_id
                        ORDER BY h.created_at ASC, h.id ASC
                    ) AS rn
                FROM visit_status_history h
                WHERE h.to_status = 'TRIAGED'
            )
            SELECT
                v.id AS visit_id,
                v.clinic_id AS clinic_id,
                v.patient_id AS patient_id,
                ft.created_at AS triaged_at,
                ft.changed_by AS changed_by
            FROM visits v
            JOIN first_triage ft
              ON ft.visit_id = v.id
             AND ft.rn = 1
            LEFT JOIN triage_assessments ta
              ON ta.visit_id = v.id
             AND ta.superseded_at IS NULL
            WHERE ta.id IS NULL
              AND v.status NOT IN ('REGISTERED', 'TRIAGED')
            """
        )
    ).fetchall()

    for row in backfill_rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO triage_assessments (
                    id,
                    clinic_id,
                    visit_id,
                    patient_id,
                    assessed_by,
                    assessed_by_role,
                    assessed_at,
                    finalized_by,
                    finalized_at,
                    triage_scale_version,
                    acuity_level,
                    chief_complaint,
                    complaint_severity,
                    triage_note,
                    missing_vitals_reason_code,
                    triage_finalize_action,
                    is_doctor_fallback,
                    created_at,
                    updated_at
                ) VALUES (
                    :id,
                    :clinic_id,
                    :visit_id,
                    :patient_id,
                    :assessed_by,
                    :assessed_by_role,
                    :assessed_at,
                    :finalized_by,
                    :finalized_at,
                    :triage_scale_version,
                    :acuity_level,
                    :chief_complaint,
                    :complaint_severity,
                    :triage_note,
                    :missing_vitals_reason_code,
                    :triage_finalize_action,
                    :is_doctor_fallback,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": uuid.uuid4(),
                "clinic_id": row.clinic_id,
                "visit_id": row.visit_id,
                "patient_id": row.patient_id,
                "assessed_by": row.changed_by,
                "assessed_by_role": "SYSTEM",
                "assessed_at": row.triaged_at,
                "finalized_by": row.changed_by,
                "finalized_at": row.triaged_at,
                "triage_scale_version": "PHC_V1",
                "acuity_level": "ROUTINE",
                "chief_complaint": "Legacy triage backfill",
                "complaint_severity": "MODERATE",
                "triage_note": "Backfilled from visit_status_history",
                "missing_vitals_reason_code": "CLINICAL_JUDGMENT",
                "triage_finalize_action": "QUEUE_FOR_CONSULTATION",
                "is_doctor_fallback": False,
                "created_at": row.triaged_at,
                "updated_at": row.triaged_at,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_triage_assessments_visit_assessed_at", table_name="triage_assessments")
    op.drop_index("ix_triage_assessments_patient", table_name="triage_assessments")
    op.drop_index("ix_triage_assessments_clinic", table_name="triage_assessments")
    op.drop_index("ix_triage_assessments_visit_active", table_name="triage_assessments")
    op.drop_table("triage_assessments")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS triage_finalize_action")
        op.execute("DROP TYPE IF EXISTS triage_fallback_reason_code")
        op.execute("DROP TYPE IF EXISTS triage_missing_vital_reason_code")
        op.execute("DROP TYPE IF EXISTS triage_complaint_severity")
        op.execute("DROP TYPE IF EXISTS triage_scale_version")
