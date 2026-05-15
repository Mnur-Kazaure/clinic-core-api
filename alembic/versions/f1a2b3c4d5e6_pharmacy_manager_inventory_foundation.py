"""pharmacy manager: inventory, stock movement, and access mode foundation

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-03-06 10:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pharmacy_inventory_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("generic_name", sa.String(length=255), nullable=False),
        sa.Column("brand_name", sa.String(length=255), nullable=True),
        sa.Column("dosage_form", sa.String(length=80), nullable=False),
        sa.Column("strength", sa.String(length=80), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=40), nullable=False),
        sa.Column("selling_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "lifecycle_status",
            sa.String(length=16),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("last_restocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
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
            name="fk_pharmacy_inventory_items_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_pharmacy_inventory_items_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_pharmacy_inventory_items_updated_by",
        ),
        sa.UniqueConstraint(
            "clinic_id",
            "generic_name",
            "brand_name",
            "dosage_form",
            "strength",
            "unit_of_measure",
            name="uq_pharmacy_inventory_identity",
        ),
        sa.CheckConstraint(
            "selling_price_minor >= 0",
            name="ck_pharmacy_inventory_items_price_non_negative",
        ),
        sa.CheckConstraint(
            "stock_quantity >= 0",
            name="ck_pharmacy_inventory_items_stock_non_negative",
        ),
        sa.CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_pharmacy_inventory_items_threshold_non_negative",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('ACTIVE','INACTIVE')",
            name="ck_pharmacy_inventory_items_lifecycle_status",
        ),
    )
    op.create_index(
        "ix_pharmacy_inventory_items_clinic_name",
        "pharmacy_inventory_items",
        ["clinic_id", "generic_name"],
    )
    op.create_index(
        "ix_pharmacy_inventory_items_clinic_status",
        "pharmacy_inventory_items",
        ["clinic_id", "lifecycle_status"],
    )

    op.create_table(
        "pharmacy_access_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column(
            "inventory_mode",
            sa.String(length=24),
            nullable=False,
            server_default="EDITABLE",
        ),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column(
            "changed_at",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_access_settings_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name="fk_pharmacy_access_settings_changed_by",
        ),
        sa.UniqueConstraint(
            "clinic_id",
            name="uq_pharmacy_access_settings_clinic",
        ),
        sa.CheckConstraint(
            "inventory_mode IN ('EDITABLE','READ_ONLY')",
            name="ck_pharmacy_access_settings_mode",
        ),
    )

    op.create_table(
        "pharmacy_stock_movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(length=24), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("stock_before", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column(
            "occurred_at",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_stock_movements_clinic",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pharmacy_inventory_items.id"],
            name="fk_pharmacy_stock_movements_inventory_item",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_pharmacy_stock_movements_actor",
        ),
        sa.CheckConstraint(
            "movement_type IN ('RESTOCK','DISPENSE','ADJUSTMENT','PRICE_UPDATE','ACTIVATED','INACTIVATED')",
            name="ck_pharmacy_stock_movements_type",
        ),
        sa.CheckConstraint(
            "stock_before >= 0 AND stock_after >= 0",
            name="ck_pharmacy_stock_movements_stock_non_negative",
        ),
        sa.CheckConstraint(
            "stock_after = stock_before + quantity_delta",
            name="ck_pharmacy_stock_movements_stock_transition",
        ),
    )
    op.create_index(
        "ix_pharmacy_stock_movements_clinic_occurred_at",
        "pharmacy_stock_movements",
        ["clinic_id", "occurred_at"],
    )
    op.create_index(
        "ix_pharmacy_stock_movements_item_occurred_at",
        "pharmacy_stock_movements",
        ["inventory_item_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pharmacy_stock_movements_item_occurred_at",
        table_name="pharmacy_stock_movements",
    )
    op.drop_index(
        "ix_pharmacy_stock_movements_clinic_occurred_at",
        table_name="pharmacy_stock_movements",
    )
    op.drop_table("pharmacy_stock_movements")

    op.drop_table("pharmacy_access_settings")

    op.drop_index(
        "ix_pharmacy_inventory_items_clinic_status",
        table_name="pharmacy_inventory_items",
    )
    op.drop_index(
        "ix_pharmacy_inventory_items_clinic_name",
        table_name="pharmacy_inventory_items",
    )
    op.drop_table("pharmacy_inventory_items")
