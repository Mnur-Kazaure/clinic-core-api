"""pharmacy catalog pricing governance

Revision ID: i9d0e1f2a3b7
Revises: h8c9d0e1f2a6
Create Date: 2026-03-28 12:20:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "i9d0e1f2a3b7"
down_revision: Union[str, Sequence[str], None] = "h8c9d0e1f2a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATALOG_LIFECYCLE_VALUES = (
    "DRAFT",
    "SUBMITTED",
    "AWAITING_CMD_APPROVAL",
    "CMD_APPROVED",
    "PRICING_PENDING",
    "PRICED",
    "ACTIVE",
    "REJECTED",
    "DEACTIVATED",
)
PRICING_STATUS_VALUES = ("NOT_CONFIGURED", "PRICED", "ACTIVE", "INACTIVE")


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_foreign_key(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {row["name"] for row in inspector.get_foreign_keys(table_name)}


def _has_unique_constraint(
    inspector: sa.Inspector, table_name: str, constraint_name: str
) -> bool:
    return constraint_name in {row["name"] for row in inspector.get_unique_constraints(table_name)}


def _catalog_code_from_uuid(value) -> str:
    return f"PHARM-{str(value).replace('-', '').upper()[:8]}"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "pharmacy_catalog_items"):
        op.create_table(
            "pharmacy_catalog_items",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("clinic_id", sa.UUID(), nullable=False),
            sa.Column("catalog_code", sa.String(length=64), nullable=False),
            sa.Column("generic_name", sa.String(length=255), nullable=False),
            sa.Column("brand_name", sa.String(length=255), nullable=True),
            sa.Column("strength", sa.String(length=80), nullable=True),
            sa.Column("dosage_form", sa.String(length=80), nullable=False),
            sa.Column("dispense_unit", sa.String(length=40), nullable=False),
            sa.Column("classification", sa.String(length=24), nullable=False, server_default="DRUG"),
            sa.Column("tracking_mode", sa.String(length=24), nullable=False, server_default="LOT_TRACKED"),
            sa.Column("requires_expiry", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="DRAFT"),
            sa.Column("billing_status", sa.String(length=24), nullable=False, server_default="NOT_CONFIGURED"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("justification", sa.Text(), nullable=False),
            sa.Column("requested_by", sa.UUID(), nullable=False),
            sa.Column("submitted_by", sa.UUID(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cmd_reviewed_by", sa.UUID(), nullable=True),
            sa.Column("cmd_reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cmd_review_note", sa.Text(), nullable=True),
            sa.Column("priced_by", sa.UUID(), nullable=True),
            sa.Column("priced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("activated_by", sa.UUID(), nullable=True),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deactivated_by", sa.UUID(), nullable=True),
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_pharmacy_catalog_items_clinic", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requested_by"], ["users.id"], name="fk_pharmacy_catalog_items_requested_by"),
            sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], name="fk_pharmacy_catalog_items_submitted_by", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["cmd_reviewed_by"], ["users.id"], name="fk_pharmacy_catalog_items_cmd_reviewed_by", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["priced_by"], ["users.id"], name="fk_pharmacy_catalog_items_priced_by", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["activated_by"], ["users.id"], name="fk_pharmacy_catalog_items_activated_by", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["deactivated_by"], ["users.id"], name="fk_pharmacy_catalog_items_deactivated_by", ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("clinic_id", "catalog_code", name="uq_pharmacy_catalog_items_clinic_code"),
            sa.CheckConstraint(
                "classification IN ('DRUG','CONSUMABLE','EQUIPMENT')",
                name="ck_pharmacy_catalog_items_classification",
            ),
            sa.CheckConstraint(
                "tracking_mode IN ('LOT_TRACKED','QUANTITY_ONLY','SERIALIZED')",
                name="ck_pharmacy_catalog_items_tracking_mode",
            ),
            sa.CheckConstraint(
                "lifecycle_status IN ('DRAFT','SUBMITTED','AWAITING_CMD_APPROVAL','CMD_APPROVED','PRICING_PENDING','PRICED','ACTIVE','REJECTED','DEACTIVATED')",
                name="ck_pharmacy_catalog_items_lifecycle_status",
            ),
            sa.CheckConstraint(
                "billing_status IN ('NOT_CONFIGURED','PRICED','ACTIVE','INACTIVE')",
                name="ck_pharmacy_catalog_items_billing_status",
            ),
        )
        op.create_index("ix_pharmacy_catalog_items_clinic_status", "pharmacy_catalog_items", ["clinic_id", "lifecycle_status"], unique=False)
        op.create_index("ix_pharmacy_catalog_items_clinic_active", "pharmacy_catalog_items", ["clinic_id", "active"], unique=False)
        op.create_index("ix_pharmacy_catalog_items_clinic_name", "pharmacy_catalog_items", ["clinic_id", "generic_name"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "pharmacy_pricing_configs"):
        op.create_table(
            "pharmacy_pricing_configs",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("clinic_id", sa.UUID(), nullable=False),
            sa.Column("catalog_item_id", sa.UUID(), nullable=False),
            sa.Column("charge_code", sa.String(length=64), nullable=False),
            sa.Column("unit_price_minor", sa.BigInteger(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
            sa.Column("effective_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="PRICED"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("configured_by", sa.UUID(), nullable=False),
            sa.Column("configured_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("activated_by", sa.UUID(), nullable=True),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deactivated_by", sa.UUID(), nullable=True),
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_pharmacy_pricing_configs_clinic", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["catalog_item_id"], ["pharmacy_catalog_items.id"], name="fk_pharmacy_pricing_configs_catalog_item", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["configured_by"], ["users.id"], name="fk_pharmacy_pricing_configs_configured_by"),
            sa.ForeignKeyConstraint(["activated_by"], ["users.id"], name="fk_pharmacy_pricing_configs_activated_by", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["deactivated_by"], ["users.id"], name="fk_pharmacy_pricing_configs_deactivated_by", ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("clinic_id", "catalog_item_id", name="uq_pharmacy_pricing_configs_clinic_catalog_item"),
            sa.UniqueConstraint("clinic_id", "charge_code", name="uq_pharmacy_pricing_configs_clinic_charge_code"),
            sa.CheckConstraint("unit_price_minor >= 0", name="ck_pharmacy_pricing_configs_unit_price_non_negative"),
            sa.CheckConstraint(
                "status IN ('NOT_CONFIGURED','PRICED','ACTIVE','INACTIVE')",
                name="ck_pharmacy_pricing_configs_status",
            ),
        )
        op.create_index("ix_pharmacy_pricing_configs_clinic_status", "pharmacy_pricing_configs", ["clinic_id", "status"], unique=False)
        op.create_index("ix_pharmacy_pricing_configs_clinic_active", "pharmacy_pricing_configs", ["clinic_id", "active"], unique=False)

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pharmacy_inventory_items"):
        if not _has_column(inspector, "pharmacy_inventory_items", "catalog_item_id"):
            op.add_column(
                "pharmacy_inventory_items",
                sa.Column("catalog_item_id", sa.UUID(), nullable=True),
            )
            inspector = sa.inspect(bind)
        if not _has_foreign_key(inspector, "pharmacy_inventory_items", "fk_pharmacy_inventory_items_catalog_item"):
            op.create_foreign_key(
                "fk_pharmacy_inventory_items_catalog_item",
                "pharmacy_inventory_items",
                "pharmacy_catalog_items",
                ["catalog_item_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _has_unique_constraint(inspector, "pharmacy_inventory_items", "uq_pharmacy_inventory_catalog_item"):
            op.create_unique_constraint(
                "uq_pharmacy_inventory_catalog_item",
                "pharmacy_inventory_items",
                ["clinic_id", "catalog_item_id"],
            )

    if _has_table(inspector, "billing_items"):
        if not _has_column(inspector, "billing_items", "pharmacy_catalog_item_id"):
            op.add_column("billing_items", sa.Column("pharmacy_catalog_item_id", sa.UUID(), nullable=True))
            inspector = sa.inspect(bind)
        if not _has_column(inspector, "billing_items", "pharmacy_pricing_config_id"):
            op.add_column("billing_items", sa.Column("pharmacy_pricing_config_id", sa.UUID(), nullable=True))
            inspector = sa.inspect(bind)
        if not _has_foreign_key(inspector, "billing_items", "fk_billing_items_pharmacy_catalog_item"):
            op.create_foreign_key(
                "fk_billing_items_pharmacy_catalog_item",
                "billing_items",
                "pharmacy_catalog_items",
                ["pharmacy_catalog_item_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _has_foreign_key(inspector, "billing_items", "fk_billing_items_pharmacy_pricing_config"):
            op.create_foreign_key(
                "fk_billing_items_pharmacy_pricing_config",
                "billing_items",
                "pharmacy_pricing_configs",
                ["pharmacy_pricing_config_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if _has_table(inspector, "prescriptions") and not _has_column(inspector, "prescriptions", "pharmacy_catalog_item_id"):
        op.add_column("prescriptions", sa.Column("pharmacy_catalog_item_id", sa.UUID(), nullable=True))
        inspector = sa.inspect(bind)
        if not _has_foreign_key(inspector, "prescriptions", "prescriptions_pharmacy_catalog_item_id_fkey"):
            op.create_foreign_key(
                "prescriptions_pharmacy_catalog_item_id_fkey",
                "prescriptions",
                "pharmacy_catalog_items",
                ["pharmacy_catalog_item_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pharmacy_inventory_items"):
        rows = bind.execute(
            sa.text(
                """
                SELECT id, clinic_id, generic_name, brand_name, dosage_form, strength,
                       unit_of_measure, classification, tracking_mode, requires_expiry,
                       selling_price_minor, currency, lifecycle_status,
                       created_by, updated_by, created_at, updated_at, catalog_item_id
                FROM pharmacy_inventory_items
                WHERE catalog_item_id IS NULL
                ORDER BY created_at ASC
                """
            )
        ).mappings().all()
        now = datetime.now(timezone.utc)
        for row in rows:
            catalog_id = uuid.uuid4()
            pricing_id = uuid.uuid4()
            created_at = row["created_at"] or now
            updated_at = row["updated_at"] or created_at
            review_actor = row["updated_by"] or row["created_by"]
            is_active = row["lifecycle_status"] == "ACTIVE"
            bind.execute(
                sa.text(
                    """
                    INSERT INTO pharmacy_catalog_items (
                        id, clinic_id, catalog_code, generic_name, brand_name, strength, dosage_form,
                        dispense_unit, classification, tracking_mode, requires_expiry,
                        lifecycle_status, billing_status, active, justification,
                        requested_by, submitted_by, submitted_at,
                        cmd_reviewed_by, cmd_reviewed_at, cmd_review_note,
                        priced_by, priced_at, activated_by, activated_at,
                        deactivated_by, deactivated_at, created_at, updated_at
                    ) VALUES (
                        :id, :clinic_id, :catalog_code, :generic_name, :brand_name, :strength, :dosage_form,
                        :dispense_unit, :classification, :tracking_mode, :requires_expiry,
                        :lifecycle_status, :billing_status, :active, :justification,
                        :requested_by, :submitted_by, :submitted_at,
                        :cmd_reviewed_by, :cmd_reviewed_at, :cmd_review_note,
                        :priced_by, :priced_at, :activated_by, :activated_at,
                        :deactivated_by, :deactivated_at, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": catalog_id,
                    "clinic_id": row["clinic_id"],
                    "catalog_code": _catalog_code_from_uuid(row["id"]),
                    "generic_name": row["generic_name"],
                    "brand_name": row["brand_name"],
                    "strength": row["strength"],
                    "dosage_form": row["dosage_form"],
                    "dispense_unit": row["unit_of_measure"],
                    "classification": row["classification"] or "DRUG",
                    "tracking_mode": row["tracking_mode"] or "LOT_TRACKED",
                    "requires_expiry": bool(row["requires_expiry"]),
                    "lifecycle_status": "ACTIVE" if is_active else "DEACTIVATED",
                    "billing_status": "ACTIVE" if is_active else "INACTIVE",
                    "active": is_active,
                    "justification": "Migrated from legacy pharmacy inventory master",
                    "requested_by": row["created_by"],
                    "submitted_by": row["created_by"],
                    "submitted_at": created_at,
                    "cmd_reviewed_by": review_actor,
                    "cmd_reviewed_at": updated_at,
                    "cmd_review_note": "Legacy inventory backfill",
                    "priced_by": review_actor,
                    "priced_at": updated_at,
                    "activated_by": review_actor if is_active else None,
                    "activated_at": updated_at if is_active else None,
                    "deactivated_by": review_actor if not is_active else None,
                    "deactivated_at": updated_at if not is_active else None,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )
            bind.execute(
                sa.text(
                    """
                    INSERT INTO pharmacy_pricing_configs (
                        id, clinic_id, catalog_item_id, charge_code, unit_price_minor, currency,
                        effective_date, status, active, configured_by, configured_at,
                        activated_by, activated_at, deactivated_by, deactivated_at,
                        created_at, updated_at
                    ) VALUES (
                        :id, :clinic_id, :catalog_item_id, :charge_code, :unit_price_minor, :currency,
                        :effective_date, :status, :active, :configured_by, :configured_at,
                        :activated_by, :activated_at, :deactivated_by, :deactivated_at,
                        :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": pricing_id,
                    "clinic_id": row["clinic_id"],
                    "catalog_item_id": catalog_id,
                    "charge_code": f"PHARM_{str(row['id']).replace('-', '').upper()[:8]}",
                    "unit_price_minor": int(row["selling_price_minor"] or 0),
                    "currency": row["currency"] or "NGN",
                    "effective_date": (created_at.date() if hasattr(created_at, "date") else now.date()),
                    "status": "ACTIVE" if is_active else "INACTIVE",
                    "active": is_active,
                    "configured_by": review_actor,
                    "configured_at": updated_at,
                    "activated_by": review_actor if is_active else None,
                    "activated_at": updated_at if is_active else None,
                    "deactivated_by": review_actor if not is_active else None,
                    "deactivated_at": updated_at if not is_active else None,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )
            bind.execute(
                sa.text(
                    "UPDATE pharmacy_inventory_items SET catalog_item_id = :catalog_item_id WHERE id = :inventory_item_id"
                ),
                {"catalog_item_id": catalog_id, "inventory_item_id": row["id"]},
            )

    if _has_table(inspector, "prescriptions") and _has_table(inspector, "pharmacy_inventory_items"):
        bind.execute(
            sa.text(
                """
                UPDATE prescriptions AS p
                SET pharmacy_catalog_item_id = pi.catalog_item_id
                FROM pharmacy_inventory_items AS pi
                WHERE p.pharmacy_catalog_item_id IS NULL
                  AND pi.catalog_item_id IS NOT NULL
                  AND pi.clinic_id = p.clinic_id
                  AND lower(pi.generic_name) = lower(p.drug_name)
                """
            )
        )

    if _has_table(inspector, "billing_items") and _has_table(inspector, "pharmacy_pricing_configs"):
        bind.execute(
            sa.text(
                """
                UPDATE billing_items AS b
                SET pharmacy_catalog_item_id = p.pharmacy_catalog_item_id,
                    pharmacy_pricing_config_id = cfg.id,
                    charge_code = COALESCE(b.charge_code, cfg.charge_code)
                FROM prescriptions AS p
                JOIN pharmacy_pricing_configs AS cfg
                  ON cfg.catalog_item_id = p.pharmacy_catalog_item_id
                 AND cfg.clinic_id = p.clinic_id
                WHERE b.id = p.billing_item_id
                  AND b.pharmacy_catalog_item_id IS NULL
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "billing_items"):
        if _has_foreign_key(inspector, "billing_items", "fk_billing_items_pharmacy_pricing_config"):
            op.drop_constraint("fk_billing_items_pharmacy_pricing_config", "billing_items", type_="foreignkey")
        if _has_foreign_key(inspector, "billing_items", "fk_billing_items_pharmacy_catalog_item"):
            op.drop_constraint("fk_billing_items_pharmacy_catalog_item", "billing_items", type_="foreignkey")
        if _has_column(inspector, "billing_items", "pharmacy_pricing_config_id"):
            op.drop_column("billing_items", "pharmacy_pricing_config_id")
        if _has_column(inspector, "billing_items", "pharmacy_catalog_item_id"):
            op.drop_column("billing_items", "pharmacy_catalog_item_id")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "prescriptions"):
        if _has_foreign_key(inspector, "prescriptions", "prescriptions_pharmacy_catalog_item_id_fkey"):
            op.drop_constraint("prescriptions_pharmacy_catalog_item_id_fkey", "prescriptions", type_="foreignkey")
        if _has_column(inspector, "prescriptions", "pharmacy_catalog_item_id"):
            op.drop_column("prescriptions", "pharmacy_catalog_item_id")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pharmacy_inventory_items"):
        if _has_foreign_key(inspector, "pharmacy_inventory_items", "fk_pharmacy_inventory_items_catalog_item"):
            op.drop_constraint("fk_pharmacy_inventory_items_catalog_item", "pharmacy_inventory_items", type_="foreignkey")
        if _has_unique_constraint(inspector, "pharmacy_inventory_items", "uq_pharmacy_inventory_catalog_item"):
            op.drop_constraint("uq_pharmacy_inventory_catalog_item", "pharmacy_inventory_items", type_="unique")
        if _has_column(inspector, "pharmacy_inventory_items", "catalog_item_id"):
            op.drop_column("pharmacy_inventory_items", "catalog_item_id")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pharmacy_pricing_configs"):
        op.drop_index("ix_pharmacy_pricing_configs_clinic_active", table_name="pharmacy_pricing_configs")
        op.drop_index("ix_pharmacy_pricing_configs_clinic_status", table_name="pharmacy_pricing_configs")
        op.drop_table("pharmacy_pricing_configs")

    if _has_table(inspector, "pharmacy_catalog_items"):
        op.drop_index("ix_pharmacy_catalog_items_clinic_name", table_name="pharmacy_catalog_items")
        op.drop_index("ix_pharmacy_catalog_items_clinic_active", table_name="pharmacy_catalog_items")
        op.drop_index("ix_pharmacy_catalog_items_clinic_status", table_name="pharmacy_catalog_items")
        op.drop_table("pharmacy_catalog_items")
