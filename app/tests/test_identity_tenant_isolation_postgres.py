import os
import uuid
import pytest
from datetime import date, timezone, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.shared.enums import Gender


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_identity_mapping_cross_tenant_fails():
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
        clinic_a = Clinic(id=uuid.uuid4(), name="Clinic A")
        clinic_b = Clinic(id=uuid.uuid4(), name="Clinic B")
        db.add_all([clinic_a, clinic_b])
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            email=f"admin.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient_a = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            full_name="Patient A",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        patient_b = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_b.id,
            full_name="Patient B",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add_all([patient_a, patient_b])
        db.commit()

        mapping = PatientIdentityMap(
            id=uuid.uuid4(),
            clinic_id=clinic_b.id,
            from_patient_id=patient_a.id,
            to_patient_id=patient_b.id,
            mapped_at=datetime.now(timezone.utc),
            mapped_by=admin.id,
        )
        db.add(mapping)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()
