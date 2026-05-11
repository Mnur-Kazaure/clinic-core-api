"""phase3 billing engine pay-gated lab workflow

Revision ID: b6c7d8e9f0a1
Revises: a9b8c7d6e5f4
Create Date: 2026-03-05 18:40:00.000000
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BILLING_ITEM_STATUS_VALUES = (
    "PENDING",
    "PAID",
    "WAIVED",
    "REFUNDED",
    "CANCELLED",
)

BILLING_REASON_CODE_VALUES = (
    "REGISTRATION_FEE",
    "SERVICE",
    "LAB_TEST",
    "MEDICATION",
    "PROCEDURE",
    "CASH",
    "CARD",
    "TRANSFER",
    "INSURANCE",
    "DISCOUNT",
    "CORRECTION",
    "REFUND",
    "WRITE_OFF",
    "REVERSAL",
    "OTHER",
)

DEFAULT_LAB_CHARGES: tuple[tuple[str, str, int], ...] = (
    ("Hemoglobin Estimation (Hb)", "Hematology & Blood", 150000),
    ("Packed Cell Volume (PCV)", "Hematology & Blood", 120000),
    ("Sickling Test", "Hematology & Blood", 100000),
    ("Blood Grouping", "Hematology & Blood", 120000),
    ("Urinalysis", "Urine & Stool", 100000),
    ("Urine Microscopy", "Urine & Stool", 120000),
    ("Stool Microscopy", "Urine & Stool", 120000),
    ("Pregnancy Test (Urine hCG)", "Screening & Metabolic", 100000),
    ("Blood Glucose (Random)", "Screening & Metabolic", 100000),
    ("Blood Glucose (Fasting)", "Screening & Metabolic", 100000),
    ("VDRL", "Infectious Disease", 120000),
    ("Hepatitis B Surface Antigen (HBsAg)", "Infectious Disease", 200000),
    ("Hepatitis C Antibody (HCV)", "Infectious Disease", 200000),
    ("HIV Test", "Infectious Disease", 150000),
    ("Sputum AFB", "Infectious Disease", 200000),
    ("Malaria Parasite Microscopy (MPS)", "Infectious Disease", 100000),
    ("Malaria Rapid Diagnostic Test (mRDT)", "Infectious Disease", 120000),
    ("Widal Test", "Infectious Disease", 120000),
    ("H. pylori Test", "Infectious Disease", 200000),
    (
        "Blood Donor Screening (Weight, Height, BP, Hb/PCV)",
        "Blood Transfusion Services",
        200000,
    ),
    (
        "Donor Blood Screening (HIV, HBsAg, HCV, VDRL)",
        "Blood Transfusion Services",
        350000,
    ),
    ("Blood Bag and Giving Set", "Blood Transfusion Services", 250000),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_code_fragment(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _build_lab_code(name: str) -> str:
    return f"LAB_{_normalize_code_fragment(name)}"


def _ensure_default_lab_catalog(bind) -> None:
    clinics = bind.execute(
        sa.text(
            """
            SELECT id, billing_currency
            FROM clinics
            """
        )
    ).fetchall()

    for clinic in clinics:
        clinic_id = clinic.id
        currency = clinic.billing_currency or "NGN"

        for name, category, default_amount_minor in DEFAULT_LAB_CHARGES:
            code = _build_lab_code(name)
            existing = bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM charge_catalog
                    WHERE clinic_id = :clinic_id
                      AND code = :code
                    LIMIT 1
                    """
                ),
                {
                    "clinic_id": clinic_id,
                    "code": code,
                },
            ).first()

            if existing is not None:
                bind.execute(
                    sa.text(
                        """
                        UPDATE charge_catalog
                        SET
                          name = :name,
                          category = :category,
                          default_amount_minor = :default_amount_minor,
                          currency = :currency,
                          active = TRUE,
                          updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": existing.id,
                        "name": name,
                        "category": category,
                        "default_amount_minor": default_amount_minor,
                        "currency": currency,
                        "updated_at": _now(),
                    },
                )
                continue

            bind.execute(
                sa.text(
                    """
                    INSERT INTO charge_catalog (
                      id,
                      clinic_id,
                      code,
                      name,
                      category,
                      default_amount_minor,
                      currency,
                      active,
                      created_at,
                      updated_at
                    )
                    VALUES (
                      :id,
                      :clinic_id,
                      :code,
                      :name,
                      :category,
                      :default_amount_minor,
                      :currency,
                      TRUE,
                      :created_at,
                      :updated_at
                    )
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "clinic_id": clinic_id,
                    "code": code,
                    "name": name,
                    "category": category,
                    "default_amount_minor": default_amount_minor,
                    "currency": currency,
                    "created_at": _now(),
                    "updated_at": _now(),
                },
            )


def _resolve_or_create_lab_charge(
    bind,
    *,
    clinic_id,
    clinic_currency: str,
    test_name: str,
    test_code: str | None,
) -> tuple[uuid.UUID, str, str, int, str]:
    normalized_code = test_code.strip() if test_code and test_code.strip() else _build_lab_code(test_name)

    by_code = bind.execute(
        sa.text(
            """
            SELECT id, code, name, default_amount_minor, currency
            FROM charge_catalog
            WHERE clinic_id = :clinic_id
              AND code = :code
              AND active = TRUE
            LIMIT 1
            """
        ),
        {
            "clinic_id": clinic_id,
            "code": normalized_code,
        },
    ).first()
    if by_code is not None:
        return (
            by_code.id,
            by_code.code,
            by_code.name,
            int(by_code.default_amount_minor),
            by_code.currency,
        )

    by_name = bind.execute(
        sa.text(
            """
            SELECT id, code, name, default_amount_minor, currency
            FROM charge_catalog
            WHERE clinic_id = :clinic_id
              AND lower(name) = lower(:name)
              AND code LIKE 'LAB_%'
              AND active = TRUE
            LIMIT 1
            """
        ),
        {
            "clinic_id": clinic_id,
            "name": test_name,
        },
    ).first()
    if by_name is not None:
        return (
            by_name.id,
            by_name.code,
            by_name.name,
            int(by_name.default_amount_minor),
            by_name.currency,
        )

    created_id = uuid.uuid4()
    now = _now()
    bind.execute(
        sa.text(
            """
            INSERT INTO charge_catalog (
              id,
              clinic_id,
              code,
              name,
              category,
              default_amount_minor,
              currency,
              active,
              created_at,
              updated_at
            )
            VALUES (
              :id,
              :clinic_id,
              :code,
              :name,
              'LAB_TEST',
              :default_amount_minor,
              :currency,
              TRUE,
              :created_at,
              :updated_at
            )
            """
        ),
        {
            "id": created_id,
            "clinic_id": clinic_id,
            "code": normalized_code,
            "name": test_name,
            "default_amount_minor": 100000,
            "currency": clinic_currency,
            "created_at": now,
            "updated_at": now,
        },
    )
    return created_id, normalized_code, test_name, 100000, clinic_currency


def _backfill_lab_requests(bind) -> None:
    clinic_rows = bind.execute(
        sa.text(
            """
            SELECT id, billing_currency
            FROM clinics
            """
        )
    ).fetchall()
    currency_by_clinic = {
        row.id: (row.billing_currency or "NGN")
        for row in clinic_rows
    }

    rows = bind.execute(
        sa.text(
            """
            SELECT
              lr.id AS lab_request_id,
              lr.clinic_id AS clinic_id,
              lr.visit_id AS visit_id,
              v.patient_id AS patient_id,
              lr.requested_by AS requested_by,
              lr.test_name AS test_name,
              lr.test_code AS test_code,
              lr.created_at AS requested_at
            FROM lab_requests lr
            JOIN visits v
              ON v.id = lr.visit_id
             AND v.clinic_id = lr.clinic_id
            WHERE lr.billing_item_id IS NULL
            ORDER BY lr.created_at ASC
            """
        )
    ).fetchall()

    for row in rows:
        clinic_id = row.clinic_id
        clinic_currency = currency_by_clinic.get(clinic_id, "NGN")
        test_name = row.test_name
        test_code = row.test_code
        requested_at = row.requested_at or _now()

        charge_id, resolved_code, resolved_name, amount_minor, resolved_currency = _resolve_or_create_lab_charge(
            bind,
            clinic_id=clinic_id,
            clinic_currency=clinic_currency,
            test_name=test_name,
            test_code=test_code,
        )

        billing_item_id = uuid.uuid4()
        bind.execute(
            sa.text(
                """
                INSERT INTO billing_items (
                  id,
                  clinic_id,
                  patient_id,
                  visit_id,
                  charge_catalog_id,
                  charge_code,
                  item_name,
                  service_type,
                  quantity,
                  unit_price_minor,
                  total_minor,
                  amount_paid_minor,
                  currency,
                  status,
                  created_by,
                  payment_reference,
                  paid_at,
                  created_at,
                  updated_at
                )
                VALUES (
                  :id,
                  :clinic_id,
                  :patient_id,
                  :visit_id,
                  :charge_catalog_id,
                  :charge_code,
                  :item_name,
                  'LAB_TEST',
                  1,
                  :unit_price_minor,
                  :total_minor,
                  :amount_paid_minor,
                  :currency,
                  'PAID',
                  :created_by,
                  :payment_reference,
                  :paid_at,
                  :created_at,
                  :updated_at
                )
                """
            ),
            {
                "id": billing_item_id,
                "clinic_id": clinic_id,
                "patient_id": row.patient_id,
                "visit_id": row.visit_id,
                "charge_catalog_id": charge_id,
                "charge_code": resolved_code,
                "item_name": resolved_name,
                "unit_price_minor": amount_minor,
                "total_minor": amount_minor,
                "amount_paid_minor": amount_minor,
                "currency": resolved_currency,
                "created_by": row.requested_by,
                "payment_reference": "MIGRATION-HISTORICAL",
                "paid_at": requested_at,
                "created_at": requested_at,
                "updated_at": _now(),
            },
        )

        bind.execute(
            sa.text(
                """
                UPDATE lab_requests
                SET
                  billing_item_id = :billing_item_id,
                  test_code = COALESCE(test_code, :resolved_code),
                  updated_at = :updated_at
                WHERE id = :lab_request_id
                """
            ),
            {
                "lab_request_id": row.lab_request_id,
                "billing_item_id": billing_item_id,
                "resolved_code": resolved_code,
                "updated_at": _now(),
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect = bind.dialect.name

    if dialect == "postgresql":
        billing_item_status = postgresql.ENUM(
            *BILLING_ITEM_STATUS_VALUES,
            name="billing_item_status",
            create_type=False,
        )
        billing_item_status.create(bind, checkfirst=True)
        payment_method_type = postgresql.ENUM(
            *BILLING_REASON_CODE_VALUES,
            name="billing_reason_code",
            create_type=False,
        )
    else:
        billing_item_status = sa.Enum(*BILLING_ITEM_STATUS_VALUES, name="billing_item_status")
        payment_method_type = sa.Enum(*BILLING_REASON_CODE_VALUES, name="billing_reason_code")

    existing_tables = set(inspector.get_table_names())

    if "billing_items" not in existing_tables:
        op.create_table(
            "billing_items",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("patient_id", sa.Uuid(), nullable=False),
            sa.Column("visit_id", sa.Uuid(), nullable=False),
            sa.Column("charge_catalog_id", sa.Uuid(), nullable=True),
            sa.Column("charge_code", sa.String(length=64), nullable=True),
            sa.Column("item_name", sa.String(length=255), nullable=False),
            sa.Column("service_type", sa.String(length=50), nullable=False, server_default="OTHER"),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("unit_price_minor", sa.BigInteger(), nullable=False),
            sa.Column("total_minor", sa.BigInteger(), nullable=False),
            sa.Column("amount_paid_minor", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("status", billing_item_status, nullable=False, server_default="PENDING"),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("payment_reference", sa.String(length=80), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("id", "clinic_id", name="uq_billing_items_id_clinic"),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_billing_items_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["patient_id", "clinic_id"],
                ["patients.id", "patients.clinic_id"],
                name="fk_billing_items_patient_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["visit_id", "clinic_id"],
                ["visits.id", "visits.clinic_id"],
                name="fk_billing_items_visit_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["charge_catalog_id"],
                ["charge_catalog.id"],
                name="fk_billing_items_charge_catalog",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
                name="fk_billing_items_created_by",
            ),
            sa.CheckConstraint("quantity > 0", name="ck_billing_items_quantity_positive"),
            sa.CheckConstraint("unit_price_minor >= 0", name="ck_billing_items_unit_price_non_negative"),
            sa.CheckConstraint("total_minor = quantity * unit_price_minor", name="ck_billing_items_total_matches"),
            sa.CheckConstraint(
                "amount_paid_minor >= 0 AND amount_paid_minor <= total_minor",
                name="ck_billing_items_amount_paid_range",
            ),
        )
        op.create_index(
            "ix_billing_items_clinic_visit_status",
            "billing_items",
            ["clinic_id", "visit_id", "status"],
        )
        op.create_index(
            "ix_billing_items_clinic_status_created",
            "billing_items",
            ["clinic_id", "status", "created_at"],
        )
        op.create_index(
            "ix_billing_items_clinic_patient",
            "billing_items",
            ["clinic_id", "patient_id"],
        )

    if "payment_receipts" not in existing_tables:
        op.create_table(
            "payment_receipts",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("patient_id", sa.Uuid(), nullable=False),
            sa.Column("visit_id", sa.Uuid(), nullable=False),
            sa.Column("receipt_number", sa.String(length=64), nullable=False),
            sa.Column("total_amount_minor", sa.BigInteger(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("payment_method", payment_method_type, nullable=False),
            sa.Column("external_ref", sa.String(length=120), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("collected_by", sa.Uuid(), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("id", "clinic_id", name="uq_payment_receipts_id_clinic"),
            sa.UniqueConstraint("clinic_id", "receipt_number", name="uq_payment_receipts_clinic_receipt"),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_payment_receipts_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["patient_id", "clinic_id"],
                ["patients.id", "patients.clinic_id"],
                name="fk_payment_receipts_patient_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["visit_id", "clinic_id"],
                ["visits.id", "visits.clinic_id"],
                name="fk_payment_receipts_visit_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["collected_by"],
                ["users.id"],
                name="fk_payment_receipts_collected_by",
            ),
        )
        op.create_index(
            "ix_payment_receipts_clinic_visit_occurred",
            "payment_receipts",
            ["clinic_id", "visit_id", "occurred_at"],
        )

    if "payment_receipt_items" not in existing_tables:
        op.create_table(
            "payment_receipt_items",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("receipt_id", sa.Uuid(), nullable=False),
            sa.Column("billing_item_id", sa.Uuid(), nullable=False),
            sa.Column("amount_minor", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("id", "clinic_id", name="uq_payment_receipt_items_id_clinic"),
            sa.UniqueConstraint(
                "receipt_id",
                "billing_item_id",
                name="uq_payment_receipt_items_receipt_billing_item",
            ),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                name="fk_payment_receipt_items_clinic",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["receipt_id", "clinic_id"],
                ["payment_receipts.id", "payment_receipts.clinic_id"],
                name="fk_payment_receipt_items_receipt",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["billing_item_id", "clinic_id"],
                ["billing_items.id", "billing_items.clinic_id"],
                name="fk_payment_receipt_items_billing_item",
                ondelete="CASCADE",
            ),
            sa.CheckConstraint("amount_minor > 0", name="ck_payment_receipt_items_amount_positive"),
        )
        op.create_index(
            "ix_payment_receipt_items_clinic_billing_item",
            "payment_receipt_items",
            ["clinic_id", "billing_item_id"],
        )

    lab_columns = {col["name"] for col in inspector.get_columns("lab_requests")}
    with op.batch_alter_table("lab_requests") as batch:
        if "test_code" not in lab_columns:
            batch.add_column(sa.Column("test_code", sa.String(length=64), nullable=True))
        if "billing_item_id" not in lab_columns:
            batch.add_column(sa.Column("billing_item_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key(
                "fk_lab_requests_billing_item_id",
                "billing_items",
                ["billing_item_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_unique_constraint(
                "uq_lab_requests_billing_item_id",
                ["billing_item_id"],
            )

    lab_indexes = {idx["name"] for idx in inspector.get_indexes("lab_requests")}
    if "ix_lab_requests_billing_item_id" not in lab_indexes:
        op.create_index(
            "ix_lab_requests_billing_item_id",
            "lab_requests",
            ["billing_item_id"],
        )

    _ensure_default_lab_catalog(bind)
    _backfill_lab_requests(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect = bind.dialect.name

    lab_indexes = {idx["name"] for idx in inspector.get_indexes("lab_requests")}
    if "ix_lab_requests_billing_item_id" in lab_indexes:
        op.drop_index("ix_lab_requests_billing_item_id", table_name="lab_requests")

    lab_columns = {col["name"] for col in inspector.get_columns("lab_requests")}
    if "billing_item_id" in lab_columns or "test_code" in lab_columns:
        with op.batch_alter_table("lab_requests") as batch:
            if "billing_item_id" in lab_columns:
                batch.drop_constraint("uq_lab_requests_billing_item_id", type_="unique")
                batch.drop_constraint("fk_lab_requests_billing_item_id", type_="foreignkey")
                batch.drop_column("billing_item_id")
            if "test_code" in lab_columns:
                batch.drop_column("test_code")

    existing_tables = set(inspector.get_table_names())

    if "payment_receipt_items" in existing_tables:
        op.drop_index("ix_payment_receipt_items_clinic_billing_item", table_name="payment_receipt_items")
        op.drop_table("payment_receipt_items")

    if "payment_receipts" in existing_tables:
        op.drop_index("ix_payment_receipts_clinic_visit_occurred", table_name="payment_receipts")
        op.drop_table("payment_receipts")

    if "billing_items" in existing_tables:
        op.drop_index("ix_billing_items_clinic_patient", table_name="billing_items")
        op.drop_index("ix_billing_items_clinic_status_created", table_name="billing_items")
        op.drop_index("ix_billing_items_clinic_visit_status", table_name="billing_items")
        op.drop_table("billing_items")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS billing_item_status")
