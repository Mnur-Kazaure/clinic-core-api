import os
import uuid
from datetime import date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.services.mrn_service import MRNService
from app.shared.enums import Gender, UserRole


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_mrn_concurrent_issue_postgres():
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
        clinic = Clinic(id=uuid.uuid4(), name="Clinic A")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin",
            role=UserRole.CLINIC_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient_a = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Patient A",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        patient_b = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Patient B",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add_all([patient_a, patient_b])
        db.commit()
        patient_a_id = patient_a.id
        patient_b_id = patient_b.id
        admin_id = admin.id
        clinic_id_value = clinic.id
    finally:
        db.close()

    def _issue(patient_id):
        session = SessionLocal()
        try:
            actor = session.query(User).filter(User.id == admin_id).first()
            mrn = MRNService(session).issue_mrn_for_patient(
                patient_id=patient_id,
                clinic_id=clinic_id_value,
                actor=actor,
            )
            return mrn.mrn
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_issue, [patient_a_id, patient_b_id]))

    assert results[0] != results[1]
