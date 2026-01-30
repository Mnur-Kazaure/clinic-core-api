"""phase4 identity resolution

Revision ID: a7b8c9d0e1f2
Revises: 6659e48611e3
Create Date: 2026-01-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "6659e48611e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        identity_state = postgresql.ENUM(
            "PROVISIONAL",
            "VERIFIED",
            "MERGED",
            "SPLIT",
            name="identity_state",
            create_type=False,
        )
        case_type = postgresql.ENUM(
            "VERIFY",
            "MERGE",
            "SPLIT",
            name="identity_case_type",
            create_type=False,
        )
        case_status = postgresql.ENUM(
            "OPEN",
            "UNDER_REVIEW",
            "APPROVED",
            "REJECTED",
            "APPLIED",
            "ROLLED_BACK",
            name="identity_case_status",
            create_type=False,
        )
        alias_type = postgresql.ENUM(
            "NAME",
            "PHONE",
            "ADDRESS",
            "GOV_ID",
            "NEXT_OF_KIN",
            "PHOTO_REF",
            name="patient_alias_type",
            create_type=False,
        )
        alias_confidence = postgresql.ENUM(
            "LOW",
            "MEDIUM",
            "HIGH",
            name="patient_alias_confidence",
            create_type=False,
        )
        alias_source = postgresql.ENUM(
            "PATIENT",
            "STAFF",
            "DOCUMENT",
            "SYSTEM",
            name="patient_alias_source",
            create_type=False,
        )
        evidence_type = postgresql.ENUM(
            "DOCUMENT_REF",
            "STAFF_WITNESS",
            "BIOMETRIC_REF",
            "PHOTO_REF",
            "SYSTEM_MATCH",
            name="identity_evidence_type",
            create_type=False,
        )
        approval_role = postgresql.ENUM(
            "ADMIN",
            "CLINIC_ADMIN",
            name="identity_approval_role",
            create_type=False,
        )
        approval_decision = postgresql.ENUM(
            "APPROVE",
            "REJECT",
            name="identity_approval_decision",
            create_type=False,
        )
        identity_state.create(bind, checkfirst=True)
        case_type.create(bind, checkfirst=True)
        case_status.create(bind, checkfirst=True)
        alias_type.create(bind, checkfirst=True)
        alias_confidence.create(bind, checkfirst=True)
        alias_source.create(bind, checkfirst=True)
        evidence_type.create(bind, checkfirst=True)
        approval_role.create(bind, checkfirst=True)
        approval_decision.create(bind, checkfirst=True)
    else:
        identity_state = sa.Enum(
            "PROVISIONAL",
            "VERIFIED",
            "MERGED",
            "SPLIT",
            name="identity_state",
        )
        case_type = sa.Enum(
            "VERIFY",
            "MERGE",
            "SPLIT",
            name="identity_case_type",
        )
        case_status = sa.Enum(
            "OPEN",
            "UNDER_REVIEW",
            "APPROVED",
            "REJECTED",
            "APPLIED",
            "ROLLED_BACK",
            name="identity_case_status",
        )
        alias_type = sa.Enum(
            "NAME",
            "PHONE",
            "ADDRESS",
            "GOV_ID",
            "NEXT_OF_KIN",
            "PHOTO_REF",
            name="patient_alias_type",
        )
        alias_confidence = sa.Enum(
            "LOW",
            "MEDIUM",
            "HIGH",
            name="patient_alias_confidence",
        )
        alias_source = sa.Enum(
            "PATIENT",
            "STAFF",
            "DOCUMENT",
            "SYSTEM",
            name="patient_alias_source",
        )
        evidence_type = sa.Enum(
            "DOCUMENT_REF",
            "STAFF_WITNESS",
            "BIOMETRIC_REF",
            "PHOTO_REF",
            "SYSTEM_MATCH",
            name="identity_evidence_type",
        )
        approval_role = sa.Enum(
            "ADMIN",
            "CLINIC_ADMIN",
            name="identity_approval_role",
        )
        approval_decision = sa.Enum(
            "APPROVE",
            "REJECT",
            name="identity_approval_decision",
        )

    op.add_column(
        "patients",
        sa.Column(
            "identity_state",
            identity_state,
            nullable=False,
            server_default="VERIFIED",
        ),
    )
    op.add_column("patients", sa.Column("created_reason", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("patients", sa.Column("verified_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_patients_verified_by",
        "patients",
        "users",
        ["verified_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "patient_aliases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("alias_type", alias_type, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", alias_confidence, nullable=False),
        sa.Column("source", alias_source, nullable=False),
        sa.Column("captured_by", sa.Uuid(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_patient_alias_patient_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_patient_alias_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["captured_by"],
            ["users.id"],
            name="fk_patient_alias_captured_by",
        ),
    )

    op.create_table(
        "identity_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("case_type", case_type, nullable=False),
        sa.Column("status", case_status, nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("primary_patient_id", sa.Uuid(), nullable=False),
        sa.Column("target_patient_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("id", "clinic_id", name="uq_identity_cases_id_clinic"),
        sa.ForeignKeyConstraint(
            ["primary_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_case_primary_patient",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_case_target_patient",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_case_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_identity_case_created_by",
        ),
    )

    op.create_table(
        "identity_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("ref", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["identity_cases.id", "identity_cases.clinic_id"],
            name="fk_identity_evidence_case",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_evidence_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_identity_evidence_added_by",
        ),
    )

    op.create_table(
        "identity_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("approver_role", approval_role, nullable=False),
        sa.Column("approver_id", sa.Uuid(), nullable=False),
        sa.Column("decision", approval_decision, nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["identity_cases.id", "identity_cases.clinic_id"],
            name="fk_identity_approval_case",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_approval_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["users.id"],
            name="fk_identity_approval_approver",
        ),
    )

    op.create_table(
        "patient_identity_map",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("from_patient_id", sa.Uuid(), nullable=False),
        sa.Column("to_patient_id", sa.Uuid(), nullable=False),
        sa.Column("mapped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mapped_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("clinic_id", "from_patient_id", name="uq_identity_map_from_patient"),
        sa.UniqueConstraint("id", "clinic_id", name="uq_identity_map_id_clinic"),
        sa.ForeignKeyConstraint(
            ["from_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_map_from_patient",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_patient_id", "clinic_id"],
            ["patients.id", "patients.clinic_id"],
            name="fk_identity_map_to_patient",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_map_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mapped_by"],
            ["users.id"],
            name="fk_identity_map_mapped_by",
        ),
        sa.CheckConstraint(
            "from_patient_id != to_patient_id",
            name="ck_identity_map_not_self",
        ),
    )

    op.create_table(
        "identity_map_revocations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("map_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revoked_by", sa.Uuid(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["map_id", "clinic_id"],
            ["patient_identity_map.id", "patient_identity_map.clinic_id"],
            name="fk_identity_revocation_map",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "clinic_id"],
            ["identity_cases.id", "identity_cases.clinic_id"],
            name="fk_identity_revocation_case",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_identity_revocation_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by"],
            ["users.id"],
            name="fk_identity_revocation_by",
        ),
    )

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION identity_append_only_block()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'identity history is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for table in (
            "patient_aliases",
            "identity_evidence",
            "identity_approvals",
            "identity_map_revocations",
        ):
            op.execute(
                f"""
                CREATE TRIGGER {table}_block_update
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION identity_append_only_block();
                """
            )
            op.execute(
                f"""
                CREATE TRIGGER {table}_block_delete
                BEFORE DELETE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION identity_append_only_block();
                """
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        for table in (
            "patient_aliases",
            "identity_evidence",
            "identity_approvals",
            "identity_map_revocations",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_block_delete ON {table};")
            op.execute(f"DROP TRIGGER IF EXISTS {table}_block_update ON {table};")
        op.execute("DROP FUNCTION IF EXISTS identity_append_only_block;")

    op.drop_table("identity_map_revocations")
    op.drop_table("patient_identity_map")
    op.drop_table("identity_approvals")
    op.drop_table("identity_evidence")
    op.drop_table("identity_cases")
    op.drop_table("patient_aliases")

    op.drop_constraint("fk_patients_verified_by", "patients", type_="foreignkey")
    op.drop_column("patients", "verified_by")
    op.drop_column("patients", "verified_at")
    op.drop_column("patients", "created_reason")
    op.drop_column("patients", "identity_state")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS identity_approval_decision")
        op.execute("DROP TYPE IF EXISTS identity_approval_role")
        op.execute("DROP TYPE IF EXISTS identity_evidence_type")
        op.execute("DROP TYPE IF EXISTS patient_alias_source")
        op.execute("DROP TYPE IF EXISTS patient_alias_confidence")
        op.execute("DROP TYPE IF EXISTS patient_alias_type")
        op.execute("DROP TYPE IF EXISTS identity_case_status")
        op.execute("DROP TYPE IF EXISTS identity_case_type")
        op.execute("DROP TYPE IF EXISTS identity_state")
