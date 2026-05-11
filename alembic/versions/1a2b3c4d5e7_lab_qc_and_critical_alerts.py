"""laboratory qc, verification policy, and critical alert safety layer

Revision ID: 1a2b3c4d5e7
Revises: 0d9c8b7a6e5f
Create Date: 2026-03-13 20:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e7"
down_revision: Union[str, Sequence[str], None] = "0d9c8b7a6e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


lab_verification_policy = postgresql.ENUM(
    "NONE",
    "OPTIONAL",
    "REQUIRED_BEFORE_RELEASE",
    "REQUIRED_IF_ABNORMAL",
    "REQUIRED_IF_CRITICAL",
    name="lab_verification_policy",
    create_type=False,
)
lab_critical_alert_type = postgresql.ENUM(
    "CRITICAL_RESULT",
    "QC_FAILURE",
    "SYSTEM_ALERT",
    name="lab_critical_alert_type",
    create_type=False,
)
lab_critical_alert_severity = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="lab_critical_alert_severity",
    create_type=False,
)
lab_critical_alert_status = postgresql.ENUM(
    "CREATED",
    "DELIVERED",
    "ACKNOWLEDGED",
    "ESCALATED",
    "RESOLVED",
    "CANCELLED",
    name="lab_critical_alert_status",
    create_type=False,
)
lab_critical_alert_event_type = postgresql.ENUM(
    "CREATED",
    "DELIVERED",
    "ACKNOWLEDGED",
    "ESCALATED",
    "RESOLVED",
    "CANCELLED",
    name="lab_critical_alert_event_type",
    create_type=False,
)
lab_qc_status = postgresql.ENUM(
    "PASS",
    "FAIL",
    "WARNING",
    name="lab_qc_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    lab_verification_policy.create(bind, checkfirst=True)
    lab_critical_alert_type.create(bind, checkfirst=True)
    lab_critical_alert_severity.create(bind, checkfirst=True)
    lab_critical_alert_status.create(bind, checkfirst=True)
    lab_critical_alert_event_type.create(bind, checkfirst=True)
    lab_qc_status.create(bind, checkfirst=True)

    op.add_column(
        "lab_result_template_fields",
        sa.Column("critical_rules_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "lab_test_config",
        sa.Column(
            "verification_policy",
            lab_verification_policy,
            nullable=False,
            server_default="OPTIONAL",
        ),
    )

    op.create_table(
        "lab_qc_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("machine_id", sa.Uuid(), nullable=True),
        sa.Column("qc_level", sa.String(length=64), nullable=False),
        sa.Column("performed_by", sa.Uuid(), nullable=False),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", lab_qc_status, nullable=False, server_default="PASS"),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_qc_runs_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["service_lines.id"],
            name="fk_lab_qc_runs_unit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"],
            ["users.id"],
            name="fk_lab_qc_runs_performed_by",
        ),
    )
    op.create_index("ix_lab_qc_runs_clinic_unit", "lab_qc_runs", ["clinic_id", "unit_id"])

    op.create_table(
        "lab_qc_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("qc_run_id", sa.Uuid(), nullable=False),
        sa.Column("analyte_name", sa.String(length=255), nullable=False),
        sa.Column("expected_min", sa.Numeric(12, 4), nullable=True),
        sa.Column("expected_max", sa.Numeric(12, 4), nullable=True),
        sa.Column("observed_value", sa.Numeric(12, 4), nullable=False),
        sa.Column("status", lab_qc_status, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["qc_run_id"],
            ["lab_qc_runs.id"],
            name="fk_lab_qc_results_run",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "qc_run_id",
            "analyte_name",
            name="uq_lab_qc_results_run_analyte",
        ),
    )

    op.create_table(
        "lab_critical_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("result_id", sa.Uuid(), nullable=True),
        sa.Column("result_value_id", sa.Uuid(), nullable=True),
        sa.Column("request_item_id", sa.Uuid(), nullable=True),
        sa.Column("visit_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=True),
        sa.Column("unit_id", sa.Uuid(), nullable=True),
        sa.Column("alert_type", lab_critical_alert_type, nullable=False),
        sa.Column(
            "severity",
            lab_critical_alert_severity,
            nullable=False,
            server_default="CRITICAL",
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("target_role", sa.String(length=64), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            lab_critical_alert_status,
            nullable=False,
            server_default="CREATED",
        ),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["lab_results.id"],
            name="fk_lab_critical_alerts_result",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["result_value_id"],
            ["lab_result_values.id"],
            name="fk_lab_critical_alerts_result_value",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["request_item_id"],
            ["lab_requests.id"],
            name="fk_lab_critical_alerts_request_item",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["visits.id"],
            name="fk_lab_critical_alerts_visit",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_lab_critical_alerts_patient",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["service_lines.id"],
            name="fk_lab_critical_alerts_unit",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_lab_critical_alerts_target_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
            name="fk_lab_critical_alerts_acknowledged_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_lab_critical_alerts_status_type",
        "lab_critical_alerts",
        ["status", "alert_type"],
    )
    op.create_index(
        "ix_lab_critical_alerts_target_role",
        "lab_critical_alerts",
        ["target_role", "status"],
    )

    op.create_table(
        "lab_critical_alert_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", lab_critical_alert_event_type, nullable=False),
        sa.Column("performed_by", sa.Uuid(), nullable=True),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["lab_critical_alerts.id"],
            name="fk_lab_critical_alert_events_alert",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"],
            ["users.id"],
            name="fk_lab_critical_alert_events_performed_by",
            ondelete="SET NULL",
        ),
    )


def downgrade() -> None:
    op.drop_table("lab_critical_alert_events")
    op.drop_index("ix_lab_critical_alerts_target_role", table_name="lab_critical_alerts")
    op.drop_index("ix_lab_critical_alerts_status_type", table_name="lab_critical_alerts")
    op.drop_table("lab_critical_alerts")
    op.drop_table("lab_qc_results")
    op.drop_index("ix_lab_qc_runs_clinic_unit", table_name="lab_qc_runs")
    op.drop_table("lab_qc_runs")
    op.drop_column("lab_test_config", "verification_policy")
    op.drop_column("lab_result_template_fields", "critical_rules_json")

    bind = op.get_bind()
    lab_qc_status.drop(bind, checkfirst=True)
    lab_critical_alert_event_type.drop(bind, checkfirst=True)
    lab_critical_alert_status.drop(bind, checkfirst=True)
    lab_critical_alert_severity.drop(bind, checkfirst=True)
    lab_critical_alert_type.drop(bind, checkfirst=True)
    lab_verification_policy.drop(bind, checkfirst=True)
