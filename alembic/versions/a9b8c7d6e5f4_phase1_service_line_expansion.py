"""phase1 service line expansion and multi-department reception

Revision ID: a9b8c7d6e5f4
Revises: c8e1f9a2b3d4
Create Date: 2026-03-04 16:10:00.000000
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "c8e1f9a2b3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _scalar_uuid(bind, stmt: sa.sql.elements.TextClause, params: dict) -> uuid.UUID | None:
    value = bind.execute(stmt, params).scalar()
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _ensure_department(bind, *, clinic_id: uuid.UUID, name: str) -> uuid.UUID:
    select_stmt = sa.text(
        """
        SELECT id
        FROM departments
        WHERE clinic_id = :clinic_id
          AND lower(name) = lower(:name)
        ORDER BY created_at ASC
        LIMIT 1
        """
    )
    found = _scalar_uuid(bind, select_stmt, {"clinic_id": clinic_id, "name": name})
    if found is not None:
        return found

    dep_id = uuid.uuid4()
    now = _now()
    bind.execute(
        sa.text(
            """
            INSERT INTO departments (id, clinic_id, name, created_at, updated_at)
            VALUES (:id, :clinic_id, :name, :created_at, :updated_at)
            """
        ),
        {
            "id": dep_id,
            "clinic_id": clinic_id,
            "name": name,
            "created_at": now,
            "updated_at": now,
        },
    )
    return dep_id


def _ensure_service_line(
    bind,
    *,
    clinic_id: uuid.UUID,
    name: str,
    parent_id: uuid.UUID | None,
    department_id: uuid.UUID | None,
    requires_doctor: bool,
    is_active: bool = True,
) -> uuid.UUID:
    select_stmt = sa.text(
        """
        SELECT id
        FROM service_lines
        WHERE clinic_id = :clinic_id
          AND lower(name) = lower(:name)
          AND (
            (:parent_id IS NULL AND parent_id IS NULL)
            OR parent_id = :parent_id
          )
        ORDER BY created_at ASC
        LIMIT 1
        """
    )
    found = _scalar_uuid(
        bind,
        select_stmt,
        {
            "clinic_id": clinic_id,
            "name": name,
            "parent_id": parent_id,
        },
    )

    if found is not None:
        bind.execute(
            sa.text(
                """
                UPDATE service_lines
                SET
                  department_id = :department_id,
                  requires_doctor = :requires_doctor,
                  is_active = :is_active,
                  updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": found,
                "department_id": department_id,
                "requires_doctor": requires_doctor,
                "is_active": is_active,
                "updated_at": _now(),
            },
        )
        return found

    service_line_id = uuid.uuid4()
    now = _now()
    bind.execute(
        sa.text(
            """
            INSERT INTO service_lines (
              id,
              clinic_id,
              name,
              parent_id,
              department_id,
              default_child_id,
              requires_doctor,
              is_active,
              created_at,
              updated_at
            )
            VALUES (
              :id,
              :clinic_id,
              :name,
              :parent_id,
              :department_id,
              NULL,
              :requires_doctor,
              :is_active,
              :created_at,
              :updated_at
            )
            """
        ),
        {
            "id": service_line_id,
            "clinic_id": clinic_id,
            "name": name,
            "parent_id": parent_id,
            "department_id": department_id,
            "requires_doctor": requires_doctor,
            "is_active": is_active,
            "created_at": now,
            "updated_at": now,
        },
    )
    return service_line_id


def _ensure_user_department(
    bind,
    *,
    user_id: uuid.UUID,
    department_id: uuid.UUID,
    is_primary: bool,
) -> None:
    existing = bind.execute(
        sa.text(
            """
            SELECT id, is_primary
            FROM user_departments
            WHERE user_id = :user_id
              AND department_id = :department_id
            LIMIT 1
            """
        ),
        {"user_id": user_id, "department_id": department_id},
    ).first()

    if existing is not None:
        if is_primary and not bool(existing.is_primary):
            bind.execute(
                sa.text(
                    """
                    UPDATE user_departments
                    SET is_primary = TRUE, updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {"id": existing.id, "updated_at": _now()},
            )
        return

    now = _now()
    bind.execute(
        sa.text(
            """
            INSERT INTO user_departments (id, user_id, department_id, is_primary, created_at, updated_at)
            VALUES (:id, :user_id, :department_id, :is_primary, :created_at, :updated_at)
            """
        ),
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "department_id": department_id,
            "is_primary": is_primary,
            "created_at": now,
            "updated_at": now,
        },
    )


def _normalize_user_department_primaries(bind) -> None:
    users = bind.execute(
        sa.text(
            """
            SELECT DISTINCT user_id
            FROM user_departments
            """
        )
    ).fetchall()

    for row in users:
        user_id = row.user_id
        records = bind.execute(
            sa.text(
                """
                SELECT id, is_primary
                FROM user_departments
                WHERE user_id = :user_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"user_id": user_id},
        ).fetchall()

        if not records:
            continue

        primary_rows = [rec for rec in records if bool(rec.is_primary)]
        if len(primary_rows) == 1:
            continue

        first_id = records[0].id
        bind.execute(
            sa.text(
                """
                UPDATE user_departments
                SET
                  is_primary = CASE WHEN id = :first_id THEN TRUE ELSE FALSE END,
                  updated_at = :updated_at
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id, "first_id": first_id, "updated_at": _now()},
        )


def _seed_default_tree(bind) -> None:
    clinics = bind.execute(sa.text("SELECT id FROM clinics")).fetchall()
    for clinic_row in clinics:
        clinic_id = (
            clinic_row.id
            if isinstance(clinic_row.id, uuid.UUID)
            else uuid.UUID(str(clinic_row.id))
        )

        gopd_dep = _ensure_department(bind, clinic_id=clinic_id, name="GOPD")
        specialist_dep = _ensure_department(bind, clinic_id=clinic_id, name="Specialist")
        maternity_dep = _ensure_department(bind, clinic_id=clinic_id, name="Maternity")
        ae_dep = _ensure_department(bind, clinic_id=clinic_id, name="A&E")

        gopd_root = _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="GOPD",
            parent_id=None,
            department_id=gopd_dep,
            requires_doctor=True,
        )
        consultation_leaf = _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="Consultation",
            parent_id=gopd_root,
            department_id=None,
            requires_doctor=True,
        )

        specialist_root = _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="Specialist",
            parent_id=None,
            department_id=specialist_dep,
            requires_doctor=True,
        )
        _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="Cardiology",
            parent_id=specialist_root,
            department_id=None,
            requires_doctor=True,
        )
        _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="Orthopaedics",
            parent_id=specialist_root,
            department_id=None,
            requires_doctor=True,
        )

        mch_root = _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="Maternal & Child Health",
            parent_id=None,
            department_id=maternity_dep,
            requires_doctor=True,
        )
        _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="ANC",
            parent_id=mch_root,
            department_id=None,
            requires_doctor=True,
        )
        _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="Maternity",
            parent_id=mch_root,
            department_id=None,
            requires_doctor=True,
        )

        _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="A&E",
            parent_id=None,
            department_id=ae_dep,
            requires_doctor=False,
        )

        legacy_root = _ensure_service_line(
            bind,
            clinic_id=clinic_id,
            name="Legacy / Unspecified",
            parent_id=None,
            department_id=None,
            requires_doctor=False,
        )

        bind.execute(
            sa.text(
                """
                UPDATE service_lines
                SET default_child_id = :default_child_id,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": gopd_root,
                "default_child_id": consultation_leaf,
                "updated_at": _now(),
            },
        )

        bind.execute(
            sa.text(
                """
                UPDATE visits
                SET service_line_id = :legacy_id
                WHERE clinic_id = :clinic_id
                  AND service_line_id IS NULL
                """
            ),
            {"legacy_id": legacy_root, "clinic_id": clinic_id},
        )

        users_with_department = bind.execute(
            sa.text(
                """
                SELECT id, department
                FROM users
                WHERE clinic_id = :clinic_id
                  AND department IS NOT NULL
                  AND length(trim(department)) > 0
                """
            ),
            {"clinic_id": clinic_id},
        ).fetchall()
        for user_row in users_with_department:
            dept_id = _ensure_department(
                bind,
                clinic_id=clinic_id,
                name=str(user_row.department).strip(),
            )
            _ensure_user_department(
                bind,
                user_id=user_row.id,
                department_id=dept_id,
                is_primary=True,
            )

        leaf_service_lines = bind.execute(
            sa.text(
                """
                SELECT sl.id
                FROM service_lines sl
                WHERE sl.clinic_id = :clinic_id
                  AND sl.is_active = TRUE
                  AND NOT EXISTS (
                    SELECT 1
                    FROM service_lines child
                    WHERE child.parent_id = sl.id
                      AND child.is_active = TRUE
                  )
                """
            ),
            {"clinic_id": clinic_id},
        ).fetchall()
        leaf_ids = [row.id for row in leaf_service_lines]

        if leaf_ids:
            clinicians = bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM users
                    WHERE clinic_id = :clinic_id
                      AND role IN ('DOCTOR', 'CHEW', 'MIDWIFE')
                    """
                ),
                {"clinic_id": clinic_id},
            ).fetchall()
            for clinician in clinicians:
                for service_line_id in leaf_ids:
                    existing = bind.execute(
                        sa.text(
                            """
                            SELECT id
                            FROM doctor_service_lines
                            WHERE doctor_id = :doctor_id
                              AND service_line_id = :service_line_id
                            LIMIT 1
                            """
                        ),
                        {
                            "doctor_id": clinician.id,
                            "service_line_id": service_line_id,
                        },
                    ).first()
                    if existing is not None:
                        continue

                    now = _now()
                    bind.execute(
                        sa.text(
                            """
                            INSERT INTO doctor_service_lines (
                              id, doctor_id, service_line_id, created_at, updated_at
                            )
                            VALUES (
                              :id, :doctor_id, :service_line_id, :created_at, :updated_at
                            )
                            """
                        ),
                        {
                            "id": uuid.uuid4(),
                            "doctor_id": clinician.id,
                            "service_line_id": service_line_id,
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

    _normalize_user_department_primaries(bind)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if "departments" not in existing_tables:
        op.create_table(
            "departments",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
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
            sa.UniqueConstraint("id", "clinic_id", name="uq_departments_id_clinic"),
            sa.UniqueConstraint("clinic_id", "name", name="uq_departments_clinic_name"),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_departments_clinic_id",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_departments_clinic_name",
            "departments",
            ["clinic_id", "name"],
        )

    if "service_lines" not in existing_tables:
        op.create_table(
            "service_lines",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("parent_id", sa.Uuid(), nullable=True),
            sa.Column("department_id", sa.Uuid(), nullable=True),
            sa.Column("default_child_id", sa.Uuid(), nullable=True),
            sa.Column(
                "requires_doctor",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
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
            sa.UniqueConstraint("id", "clinic_id", name="uq_service_lines_id_clinic"),
            sa.UniqueConstraint(
                "clinic_id",
                "name",
                "parent_id",
                name="uq_service_lines_clinic_name_parent",
            ),
            sa.CheckConstraint("(parent_id IS NULL) OR (parent_id != id)", name="ck_service_lines_parent_self"),
            sa.CheckConstraint(
                "(default_child_id IS NULL) OR (default_child_id != id)",
                name="ck_service_lines_default_child_self",
            ),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_service_lines_clinic_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["parent_id"],
                ["service_lines.id"],
                name="fk_service_lines_parent_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["default_child_id"],
                ["service_lines.id"],
                name="fk_service_lines_default_child_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["department_id"],
                ["departments.id"],
                name="fk_service_lines_department_id",
                ondelete="SET NULL",
            ),
        )
        op.create_index(
            "ix_service_lines_clinic_parent_active",
            "service_lines",
            ["clinic_id", "parent_id", "is_active"],
        )
        op.create_index(
            "ix_service_lines_clinic_department_active",
            "service_lines",
            ["clinic_id", "department_id", "is_active"],
        )

    if "user_departments" not in existing_tables:
        op.create_table(
            "user_departments",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("department_id", sa.Uuid(), nullable=False),
            sa.Column(
                "is_primary",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
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
            sa.UniqueConstraint(
                "user_id",
                "department_id",
                name="uq_user_departments_user_department",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_user_departments_user_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["department_id"],
                ["departments.id"],
                name="fk_user_departments_department_id",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_user_departments_user_primary",
            "user_departments",
            ["user_id", "is_primary"],
        )

    if "doctor_service_lines" not in existing_tables:
        op.create_table(
            "doctor_service_lines",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("doctor_id", sa.Uuid(), nullable=False),
            sa.Column("service_line_id", sa.Uuid(), nullable=False),
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
            sa.UniqueConstraint(
                "doctor_id",
                "service_line_id",
                name="uq_doctor_service_lines_doctor_service_line",
            ),
            sa.ForeignKeyConstraint(
                ["doctor_id"],
                ["users.id"],
                name="fk_doctor_service_lines_doctor_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["service_line_id"],
                ["service_lines.id"],
                name="fk_doctor_service_lines_service_line_id",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_doctor_service_lines_service_line",
            "doctor_service_lines",
            ["service_line_id"],
        )

    visit_columns = {column["name"] for column in inspector.get_columns("visits")}
    with op.batch_alter_table("visits") as batch:
        if "service_line_id" not in visit_columns:
            batch.add_column(sa.Column("service_line_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key(
                "fk_visits_service_line_id",
                "service_lines",
                ["service_line_id"],
                ["id"],
            )
        batch.alter_column(
            "assigned_doctor_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("visits")}
    if "ix_visits_clinic_service_line_id_status" not in existing_indexes:
        op.create_index(
            "ix_visits_clinic_service_line_id_status",
            "visits",
            ["clinic_id", "service_line_id", "status"],
        )

    _seed_default_tree(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("visits")}
    if "ix_visits_clinic_service_line_id_status" in existing_indexes:
        op.drop_index("ix_visits_clinic_service_line_id_status", table_name="visits")

    visit_columns = {column["name"] for column in inspector.get_columns("visits")}
    if "service_line_id" in visit_columns:
        with op.batch_alter_table("visits") as batch:
            batch.drop_constraint("fk_visits_service_line_id", type_="foreignkey")
            batch.drop_column("service_line_id")

    null_owner_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM visits
            WHERE assigned_doctor_id IS NULL
            """
        )
    ).scalar() or 0
    if int(null_owner_count) > 0:
        raise RuntimeError(
            "Cannot downgrade: visits.assigned_doctor_id contains NULL rows."
        )

    with op.batch_alter_table("visits") as batch:
        batch.alter_column(
            "assigned_doctor_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )

    existing_tables = set(inspector.get_table_names())
    if "doctor_service_lines" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("doctor_service_lines")}
        if "ix_doctor_service_lines_service_line" in indexes:
            op.drop_index("ix_doctor_service_lines_service_line", table_name="doctor_service_lines")
        op.drop_table("doctor_service_lines")

    if "user_departments" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("user_departments")}
        if "ix_user_departments_user_primary" in indexes:
            op.drop_index("ix_user_departments_user_primary", table_name="user_departments")
        op.drop_table("user_departments")

    if "service_lines" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("service_lines")}
        if "ix_service_lines_clinic_department_active" in indexes:
            op.drop_index("ix_service_lines_clinic_department_active", table_name="service_lines")
        if "ix_service_lines_clinic_parent_active" in indexes:
            op.drop_index("ix_service_lines_clinic_parent_active", table_name="service_lines")
        op.drop_table("service_lines")

    if "departments" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("departments")}
        if "ix_departments_clinic_name" in indexes:
            op.drop_index("ix_departments_clinic_name", table_name="departments")
        op.drop_table("departments")
