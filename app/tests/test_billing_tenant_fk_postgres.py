import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.shared.enums import Gender, UserRole, VisitStatus, BillingEntryType, BillingReasonCode


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_billing_tenant_fk_enforced():
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
        clinic_a = Clinic(id=uuid.uuid4(), name="Clinic A", billing_currency="NGN")
        clinic_b = Clinic(id=uuid.uuid4(), name="Clinic B", billing_currency="NGN")
        db.add_all([clinic_a, clinic_b])
        db.commit()

        doctor = User(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            email=f"doctor.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Clinic A Doctor",
            role=UserRole.DOCTOR,
            is_active=True,
        )
        db.add(doctor)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            full_name="Tenant Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        visit = Visit(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            patient_id=patient.id,
            assigned_doctor_id=doctor.id,
            status=VisitStatus.IN_CONSULTATION,
        )
        db.add(visit)
        db.commit()

        entry = BillingLedgerEntry(
            id=uuid.uuid4(),
            clinic_id=clinic_b.id,
            patient_id=patient.id,
            visit_id=visit.id,
            admission_id=None,
            entry_type=BillingEntryType.CHARGE,
            amount_minor=1500,
            currency="NGN",
            description="Cross-tenant charge",
            reason_code=BillingReasonCode.SERVICE,
            external_ref=None,
            related_entry_id=None,
            actor_id=doctor.id,
            actor_role=doctor.role,
            occurred_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
