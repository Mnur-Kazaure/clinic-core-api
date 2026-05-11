"""laboratory foundation layer: templates, specimens, routing, and audit

Revision ID: 0d9c8b7a6e5f
Revises: f1a2b3c4d5e6
Create Date: 2026-03-13 18:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0d9c8b7a6e5f"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


lab_request_workflow_status = postgresql.ENUM(
    "ORDERED",
    "PAID",
    "AWAITING_SPECIMEN",
    "IN_ANALYSIS",
    "RESULT_ENTERED",
    "VERIFIED",
    "RELEASED",
    "COMPLETED",
    name="lab_request_workflow_status",
    create_type=False,
)
lab_result_template_type = postgresql.ENUM(
    "NUMERIC",
    "QUALITATIVE",
    "SELECT",
    "TEXT",
    "PANEL",
    "NARRATIVE",
    "ATTACHMENT",
    name="lab_result_template_type",
    create_type=False,
)
lab_result_field_type = postgresql.ENUM(
    "STRING",
    "NUMBER",
    "BOOLEAN",
    "SELECT",
    "TEXT",
    "JSON",
    "ATTACHMENT",
    name="lab_result_field_type",
    create_type=False,
)
lab_result_lifecycle_status = postgresql.ENUM(
    "DRAFT",
    "SUBMITTED",
    "VERIFIED",
    "REJECTED",
    "RELEASED",
    "AMENDED",
    name="lab_result_lifecycle_status",
    create_type=False,
)
lab_specimen_status = postgresql.ENUM(
    "PENDING_COLLECTION",
    "COLLECTED",
    "RECEIVED",
    "IN_PROCESS",
    "REJECTED",
    "LOST",
    "DISPOSED",
    name="lab_specimen_status",
    create_type=False,
)
lab_specimen_rejection_reason_code = postgresql.ENUM(
    "INSUFFICIENT_SAMPLE",
    "HEMOLYSED_SAMPLE",
    "WRONG_CONTAINER",
    "MISLABELLED_SPECIMEN",
    "CONTAMINATED_SAMPLE",
    "EXPIRED_SAMPLE",
    "OTHER",
    name="lab_specimen_rejection_reason_code",
    create_type=False,
)
lab_specimen_event_type = postgresql.ENUM(
    "CREATED",
    "LABEL_PRINTED",
    "COLLECTED",
    "RECEIVED",
    "ROUTED_TO_UNIT",
    "REJECTED",
    "RECOLLECTION_REQUESTED",
    "LOST",
    "ANALYSIS_STARTED",
    "ANALYSIS_COMPLETED",
    "DISPOSED",
    name="lab_specimen_event_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    lab_request_workflow_status.create(bind, checkfirst=True)
    lab_result_template_type.create(bind, checkfirst=True)
    lab_result_field_type.create(bind, checkfirst=True)
    lab_result_lifecycle_status.create(bind, checkfirst=True)
    lab_specimen_status.create(bind, checkfirst=True)
    lab_specimen_rejection_reason_code.create(bind, checkfirst=True)
    lab_specimen_event_type.create(bind, checkfirst=True)

    op.create_table(
        "lab_result_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("result_type", lab_result_template_type, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint(
            "code",
            "version",
            name="uq_lab_result_templates_code_version",
        ),
    )

    op.create_table(
        "lab_result_template_fields",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("field_code", sa.String(length=64), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("field_type", lab_result_field_type, nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("reference_range_text", sa.String(length=255), nullable=True),
        sa.Column("reference_min", sa.Numeric(12, 4), nullable=True),
        sa.Column("reference_max", sa.Numeric(12, 4), nullable=True),
        sa.Column("reference_unit", sa.String(length=32), nullable=True),
        sa.Column("options_json", sa.JSON(), nullable=True),
        sa.Column("validation_rules_json", sa.JSON(), nullable=True),
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
            ["template_id"],
            ["lab_result_templates.id"],
            name="fk_lab_result_template_fields_template",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "template_id",
            "field_code",
            name="uq_lab_result_template_fields_template_code",
        ),
        sa.CheckConstraint(
            "display_order >= 1",
            name="ck_lab_result_template_fields_display_order",
        ),
    )

    op.create_table(
        "lab_test_catalog",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("test_code", sa.String(length=64), nullable=False),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("specimen_type", sa.String(length=80), nullable=False),
        sa.Column("default_template_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            name="fk_lab_test_catalog_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["service_lines.id"],
            name="fk_lab_test_catalog_unit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["default_template_id"],
            ["lab_result_templates.id"],
            name="fk_lab_test_catalog_default_template",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("clinic_id", "test_code", name="uq_lab_test_catalog_clinic_code"),
        sa.UniqueConstraint("clinic_id", "test_name", name="uq_lab_test_catalog_clinic_name"),
    )
    op.create_index(
        "ix_lab_test_catalog_clinic_unit",
        "lab_test_catalog",
        ["clinic_id", "unit_id"],
    )
    op.create_index(
        "ix_lab_test_catalog_clinic_name",
        "lab_test_catalog",
        ["clinic_id", "test_name"],
    )

    op.create_table(
        "lab_test_config",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("catalog_test_id", sa.Uuid(), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
        sa.Column("turnaround_time_minutes", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("billing_name", sa.String(length=255), nullable=False),
        sa.Column("critical_rules_json", sa.JSON(), nullable=True),
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
            name="fk_lab_test_config_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_test_id"],
            ["lab_test_catalog.id"],
            name="fk_lab_test_config_catalog_test",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "clinic_id",
            "catalog_test_id",
            name="uq_lab_test_config_clinic_catalog_test",
        ),
        sa.CheckConstraint(
            "price_minor >= 0",
            name="ck_lab_test_config_price_non_negative",
        ),
        sa.CheckConstraint(
            "turnaround_time_minutes >= 0",
            name="ck_lab_test_config_turnaround_non_negative",
        ),
    )

    op.add_column(
        "lab_requests",
        sa.Column(
            "lab_test_catalog_id",
            sa.Uuid(),
            nullable=True,
        ),
    )
    op.add_column(
        "lab_requests",
        sa.Column(
            "lab_test_config_id",
            sa.Uuid(),
            nullable=True,
        ),
    )
    op.add_column(
        "lab_requests",
        sa.Column(
            "target_unit_id",
            sa.Uuid(),
            nullable=True,
        ),
    )
    op.add_column(
        "lab_requests",
        sa.Column(
            "workflow_status",
            lab_request_workflow_status,
            nullable=False,
            server_default="ORDERED",
        ),
    )
    op.create_foreign_key(
        "fk_lab_requests_catalog",
        "lab_requests",
        "lab_test_catalog",
        ["lab_test_catalog_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lab_requests_config",
        "lab_requests",
        "lab_test_config",
        ["lab_test_config_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lab_requests_target_unit",
        "lab_requests",
        "service_lines",
        ["target_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_lab_requests_workflow_status",
        "lab_requests",
        ["workflow_status"],
    )
    op.create_index(
        "ix_lab_requests_target_unit",
        "lab_requests",
        ["target_unit_id"],
    )
    op.execute(
        """
        UPDATE lab_requests
        SET workflow_status = CASE
            WHEN status = 'COMPLETED' THEN 'COMPLETED'::lab_request_workflow_status
            ELSE 'ORDERED'::lab_request_workflow_status
        END
        """
    )

    op.add_column(
        "lab_results",
        sa.Column("request_item_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column("template_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column("template_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column(
            "status",
            lab_result_lifecycle_status,
            nullable=False,
            server_default="RELEASED",
        ),
    )
    op.add_column(
        "lab_results",
        sa.Column("entered_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column(
            "entered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "lab_results",
        sa.Column("verified_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column("released_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "lab_results",
        sa.Column("amended_from_result_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_lab_results_request_item",
        "lab_results",
        "lab_requests",
        ["request_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lab_results_template",
        "lab_results",
        "lab_result_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lab_results_entered_by",
        "lab_results",
        "users",
        ["entered_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lab_results_verified_by",
        "lab_results",
        "users",
        ["verified_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lab_results_released_by",
        "lab_results",
        "users",
        ["released_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lab_results_amended_from",
        "lab_results",
        "lab_results",
        ["amended_from_result_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_lab_results_request_item_id", "lab_results", ["request_item_id"])
    op.create_index("ix_lab_results_status", "lab_results", ["status"])
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE lab_results DISABLE TRIGGER lab_results_block_update_signed")
    try:
        op.execute(
            """
            UPDATE lab_results
            SET
                request_item_id = lab_request_id,
                entered_by = technician_id,
                entered_at = COALESCE(created_at, now()),
                released_by = technician_id,
                released_at = COALESCE(signed_at, created_at, now()),
                status = CASE
                    WHEN record_status = 'DRAFT' THEN 'DRAFT'::lab_result_lifecycle_status
                    WHEN record_status = 'AMENDED' THEN 'AMENDED'::lab_result_lifecycle_status
                    WHEN record_status = 'VOIDED' THEN 'REJECTED'::lab_result_lifecycle_status
                    ELSE 'RELEASED'::lab_result_lifecycle_status
                END
            """
        )
    finally:
        if bind.dialect.name == "postgresql":
            op.execute("ALTER TABLE lab_results ENABLE TRIGGER lab_results_block_update_signed")

    op.create_table(
        "lab_specimens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("accession_number", sa.String(length=32), nullable=False),
        sa.Column("request_item_id", sa.Uuid(), nullable=False),
        sa.Column("target_unit_id", sa.Uuid(), nullable=False),
        sa.Column("specimen_type", sa.String(length=80), nullable=False),
        sa.Column("specimen_source", sa.String(length=80), nullable=False),
        sa.Column("container_type", sa.String(length=80), nullable=True),
        sa.Column("collection_site", sa.String(length=80), nullable=True),
        sa.Column("specimen_sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("specimen_label_suffix", sa.String(length=16), nullable=True),
        sa.Column("collected_by", sa.Uuid(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by", sa.Uuid(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            lab_specimen_status,
            nullable=False,
            server_default="PENDING_COLLECTION",
        ),
        sa.Column("rejection_reason_code", lab_specimen_rejection_reason_code, nullable=True),
        sa.Column("rejection_reason_text", sa.Text(), nullable=True),
        sa.Column("rejected_by", sa.Uuid(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_lab_specimens_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_item_id"],
            ["lab_requests.id"],
            name="fk_lab_specimens_request_item",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_unit_id"],
            ["service_lines.id"],
            name="fk_lab_specimens_target_unit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["collected_by"],
            ["users.id"],
            name="fk_lab_specimens_collected_by",
        ),
        sa.ForeignKeyConstraint(
            ["received_by"],
            ["users.id"],
            name="fk_lab_specimens_received_by",
        ),
        sa.ForeignKeyConstraint(
            ["rejected_by"],
            ["users.id"],
            name="fk_lab_specimens_rejected_by",
        ),
        sa.UniqueConstraint("accession_number", name="uq_lab_specimens_accession"),
        sa.UniqueConstraint(
            "request_item_id",
            "specimen_sequence",
            name="uq_lab_specimens_request_sequence",
        ),
        sa.CheckConstraint(
            "specimen_sequence >= 1",
            name="ck_lab_specimens_sequence_positive",
        ),
    )
    op.create_index(
        "ix_lab_specimens_clinic_status_unit",
        "lab_specimens",
        ["clinic_id", "status", "target_unit_id"],
    )

    op.create_table(
        "lab_specimen_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("specimen_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", lab_specimen_event_type, nullable=False),
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
            ["specimen_id"],
            ["lab_specimens.id"],
            name="fk_lab_specimen_events_specimen",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"],
            ["users.id"],
            name="fk_lab_specimen_events_performed_by",
        ),
    )

    op.create_table(
        "lab_result_values",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("template_field_id", sa.Uuid(), nullable=False),
        sa.Column("value_string", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(12, 4), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("abnormal_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("critical_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
            name="fk_lab_result_values_result",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_field_id"],
            ["lab_result_template_fields.id"],
            name="fk_lab_result_values_template_field",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "result_id",
            "template_field_id",
            name="uq_lab_result_values_result_field",
        ),
    )


def downgrade() -> None:
    op.drop_table("lab_result_values")
    op.drop_table("lab_specimen_events")
    op.drop_index("ix_lab_specimens_clinic_status_unit", table_name="lab_specimens")
    op.drop_table("lab_specimens")

    op.drop_index("ix_lab_results_status", table_name="lab_results")
    op.drop_index("ix_lab_results_request_item_id", table_name="lab_results")
    op.drop_constraint("fk_lab_results_amended_from", "lab_results", type_="foreignkey")
    op.drop_constraint("fk_lab_results_released_by", "lab_results", type_="foreignkey")
    op.drop_constraint("fk_lab_results_verified_by", "lab_results", type_="foreignkey")
    op.drop_constraint("fk_lab_results_entered_by", "lab_results", type_="foreignkey")
    op.drop_constraint("fk_lab_results_template", "lab_results", type_="foreignkey")
    op.drop_constraint("fk_lab_results_request_item", "lab_results", type_="foreignkey")
    op.drop_column("lab_results", "amended_from_result_id")
    op.drop_column("lab_results", "released_at")
    op.drop_column("lab_results", "released_by")
    op.drop_column("lab_results", "verified_at")
    op.drop_column("lab_results", "verified_by")
    op.drop_column("lab_results", "entered_at")
    op.drop_column("lab_results", "entered_by")
    op.drop_column("lab_results", "status")
    op.drop_column("lab_results", "template_version")
    op.drop_column("lab_results", "template_id")
    op.drop_column("lab_results", "request_item_id")

    op.drop_index("ix_lab_requests_target_unit", table_name="lab_requests")
    op.drop_index("ix_lab_requests_workflow_status", table_name="lab_requests")
    op.drop_constraint("fk_lab_requests_target_unit", "lab_requests", type_="foreignkey")
    op.drop_constraint("fk_lab_requests_config", "lab_requests", type_="foreignkey")
    op.drop_constraint("fk_lab_requests_catalog", "lab_requests", type_="foreignkey")
    op.drop_column("lab_requests", "workflow_status")
    op.drop_column("lab_requests", "target_unit_id")
    op.drop_column("lab_requests", "lab_test_config_id")
    op.drop_column("lab_requests", "lab_test_catalog_id")

    op.drop_table("lab_test_config")
    op.drop_index("ix_lab_test_catalog_clinic_name", table_name="lab_test_catalog")
    op.drop_index("ix_lab_test_catalog_clinic_unit", table_name="lab_test_catalog")
    op.drop_table("lab_test_catalog")
    op.drop_table("lab_result_template_fields")
    op.drop_table("lab_result_templates")

    bind = op.get_bind()
    lab_specimen_event_type.drop(bind, checkfirst=True)
    lab_specimen_rejection_reason_code.drop(bind, checkfirst=True)
    lab_specimen_status.drop(bind, checkfirst=True)
    lab_result_lifecycle_status.drop(bind, checkfirst=True)
    lab_result_field_type.drop(bind, checkfirst=True)
    lab_result_template_type.drop(bind, checkfirst=True)
    lab_request_workflow_status.drop(bind, checkfirst=True)
