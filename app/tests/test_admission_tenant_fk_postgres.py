import os
import uuid
import pytest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.admission import Admission
from app.shared.enums import AdmissionType, AdmissionStatus, Gender


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_admission_tenant_fk_violation():
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

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            full_name="Tenant Patient",
            date_of_birth=datetime(2000, 1, 1).date(),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        # Mismatched clinic_id should violate composite FK
        admission = Admission(
            id=uuid.uuid4(),
            clinic_id=clinic_b.id,
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        db.add(admission)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()
