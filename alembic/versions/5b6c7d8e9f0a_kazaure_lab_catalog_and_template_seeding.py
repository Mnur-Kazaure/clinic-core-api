"""kazaure lab catalog and template seeding

Revision ID: 5b6c7d8e9f0a
Revises: 4a5b6c7d8e9f
Create Date: 2026-03-18 23:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.services.lab_catalog_seed_service import LabCatalogSeedService


# revision identifiers, used by Alembic.
revision = "5b6c7d8e9f0a"
down_revision = "4a5b6c7d8e9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                "ALTER TYPE lab_result_template_type ADD VALUE IF NOT EXISTS 'MIXED'"
            )
            op.execute(
                "ALTER TYPE lab_result_template_type ADD VALUE IF NOT EXISTS 'MIXED_STRUCTURED'"
            )

    op.add_column(
        "lab_test_config",
        sa.Column("unit_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "lab_test_config",
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE lab_test_config AS cfg
            SET unit_id = cat.unit_id
            FROM lab_test_catalog AS cat
            WHERE cfg.catalog_test_id = cat.id
              AND cfg.unit_id IS NULL
            """
        )
    )

    op.alter_column("lab_test_config", "unit_id", nullable=False)
    op.create_foreign_key(
        "fk_lab_test_config_unit",
        "lab_test_config",
        "service_lines",
        ["unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_lab_test_config_display_order_positive",
        "lab_test_config",
        "display_order >= 1",
    )
    op.create_index(
        "ix_lab_test_config_clinic_unit_display",
        "lab_test_config",
        ["clinic_id", "unit_id", "display_order"],
    )

    session = Session(bind=bind)
    try:
        clinic_ids = [row[0] for row in session.execute(sa.text("SELECT id FROM clinics")).all()]
        seeder = LabCatalogSeedService(session)
        for clinic_id in clinic_ids:
            seeder.seed_kazaure_catalog(clinic_id=clinic_id, commit=False)
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    op.drop_index("ix_lab_test_config_clinic_unit_display", table_name="lab_test_config")
    op.drop_constraint(
        "ck_lab_test_config_display_order_positive",
        "lab_test_config",
        type_="check",
    )
    op.drop_constraint("fk_lab_test_config_unit", "lab_test_config", type_="foreignkey")
    op.drop_column("lab_test_config", "display_order")
    op.drop_column("lab_test_config", "unit_id")
