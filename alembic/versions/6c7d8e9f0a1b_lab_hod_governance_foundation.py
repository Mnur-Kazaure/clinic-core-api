"""lab hod governance foundation

Revision ID: 6c7d8e9f0a1b
Revises: 5b6c7d8e9f0a
Create Date: 2026-03-19 10:40:00.000000
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.shared.enums import (
    LabConfigurationRequestStatus,
    LabConfigurationRequestType,
    LabStaffAssignmentStatus,
    UserRole,
)


# revision identifiers, used by Alembic.
revision = "6c7d8e9f0a1b"
down_revision = "5b6c7d8e9f0a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_staff_assignment_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assignment_status",
            sa.Enum(LabStaffAssignmentStatus, name="lab_staff_assignment_status"),
            nullable=False,
            server_default=LabStaffAssignmentStatus.ACTIVE.value,
        ),
        sa.Column("coverage_note", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_staff_assignment_profiles_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_lab_staff_assignment_profiles_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_lab_staff_assignment_profiles_updated_by",
        ),
        sa.UniqueConstraint(
            "clinic_id",
            "user_id",
            name="uq_lab_staff_assignment_profiles_clinic_user",
        ),
    )
    op.create_index(
        "ix_lab_staff_assignment_profiles_clinic_status",
        "lab_staff_assignment_profiles",
        ["clinic_id", "assignment_status"],
    )

    op.create_table(
        "lab_configuration_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column(
            "request_type",
            sa.Enum(LabConfigurationRequestType, name="lab_configuration_request_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(LabConfigurationRequestStatus, name="lab_configuration_request_status"),
            nullable=False,
            server_default=LabConfigurationRequestStatus.PENDING.value,
        ),
        sa.Column(
            "department_name",
            sa.String(length=120),
            nullable=False,
            server_default="Medical Laboratory",
        ),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("linked_staff_id", sa.Uuid(), nullable=True),
        sa.Column("linked_unit_id", sa.Uuid(), nullable=True),
        sa.Column("linked_test_code", sa.String(length=64), nullable=True),
        sa.Column("request_payload_json", sa.JSON(), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_configuration_requests_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_lab_configuration_requests_requested_by",
        ),
        sa.ForeignKeyConstraint(
            ["linked_staff_id"],
            ["users.id"],
            name="fk_lab_configuration_requests_linked_staff",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["linked_unit_id"],
            ["service_lines.id"],
            name="fk_lab_configuration_requests_linked_unit",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_lab_configuration_requests_resolved_by",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "id",
            "clinic_id",
            name="uq_lab_configuration_requests_id_clinic",
        ),
    )
    op.create_index(
        "ix_lab_configuration_requests_clinic_status_created",
        "lab_configuration_requests",
        ["clinic_id", "status", "created_at"],
    )

    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        users = (
            session.execute(
                sa.text(
                    """
                    SELECT id, clinic_id
                    FROM users
                    WHERE role IN :roles
                    """
                ).bindparams(
                    sa.bindparam(
                        "roles",
                        expanding=True,
                    )
                ),
                {
                    "roles": [
                        UserRole.LAB.value,
                        UserRole.LAB_TECH.value,
                        UserRole.LAB_SCIENTIST.value,
                        UserRole.LAB_SUPERVISOR.value,
                        UserRole.LAB_MANAGER.value,
                    ]
                },
            )
            .all()
        )
        profile_table = sa.table(
            "lab_staff_assignment_profiles",
            sa.column("id", sa.Uuid()),
            sa.column("clinic_id", sa.Uuid()),
            sa.column("user_id", sa.Uuid()),
            sa.column("assignment_status", sa.String()),
        )
        if users:
            op.bulk_insert(
                profile_table,
                [
                    {
                        "id": uuid.uuid4(),
                        "clinic_id": row.clinic_id,
                        "user_id": row.id,
                        "assignment_status": LabStaffAssignmentStatus.ACTIVE.value,
                    }
                    for row in users
                ],
            )
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    op.drop_index(
        "ix_lab_configuration_requests_clinic_status_created",
        table_name="lab_configuration_requests",
    )
    op.drop_table("lab_configuration_requests")
    op.drop_index(
        "ix_lab_staff_assignment_profiles_clinic_status",
        table_name="lab_staff_assignment_profiles",
    )
    op.drop_table("lab_staff_assignment_profiles")
