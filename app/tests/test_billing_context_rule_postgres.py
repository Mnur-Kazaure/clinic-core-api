import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.shared.enums import Gender, UserRole, BillingEntryType, BillingReasonCode


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_billing_context_rule_entry_type_aware():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL)
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Clinic A", billing_currency="NGN")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Billing Admin",
            role=UserRole.CLINIC_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Context Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        charge = BillingLedgerEntry(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            visit_id=None,
            admission_id=None,
            entry_type=BillingEntryType.CHARGE,
            amount_minor=1200,
            currency="NGN",
            description="Orphan charge",
            reason_code=BillingReasonCode.SERVICE,
            external_ref=None,
            related_entry_id=None,
            actor_id=admin.id,
            actor_role=admin.role,
            occurred_at=datetime.now(timezone.utc),
        )
        db.add(charge)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        payment = BillingLedgerEntry(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            visit_id=None,
            admission_id=None,
            entry_type=BillingEntryType.PAYMENT,
            amount_minor=-500,
            currency="NGN",
            description="Patient payment",
            reason_code=BillingReasonCode.CASH,
            external_ref=None,
            related_entry_id=None,
            actor_id=admin.id,
            actor_role=admin.role,
            occurred_at=datetime.now(timezone.utc),
        )
        db.add(payment)
        db.commit()
    finally:
        db.close()
