import os
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.schemas.visit import VisitCreateRequest
from app.services.visit.service import VisitService
from app.shared.enums import Gender, UserRole, VisitStatus


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


def _socket_url(engine_url: str) -> str:
    if os.getenv("USE_PG_SOCKET") != "1":
        return engine_url
    parsed = urlparse(engine_url)
    if parsed.hostname in {"localhost", "127.0.0.1"}:
        dbname = parsed.path.lstrip("/")
        user = parsed.username or "postgres"
        if parsed.password:
            return f"postgresql+psycopg2://{user}:{parsed.password}@/{dbname}"
        return f"postgresql+psycopg2://{user}@/{dbname}"
    return engine_url


def _migrate(engine_url: str) -> None:
    engine_url = _socket_url(engine_url)
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", engine_url)
    original_database_url = os.environ.get("DATABASE_URL")
    original_pgpassword = os.environ.get("PGPASSWORD")
    os.environ["DATABASE_URL"] = engine_url
    os.environ["PGPASSWORD"] = "postgres"
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url
        if original_pgpassword is None:
            os.environ.pop("PGPASSWORD", None)
        else:
            os.environ["PGPASSWORD"] = original_pgpassword


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_start_visit_blocked_when_active():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Test Clinic")
        db.add(clinic)
        db.commit()

        doctor = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"doctor_{clinic.id}@example.test",
            password_hash="test",
            full_name="Doctor One",
            role=UserRole.DOCTOR.value,
            is_active=True,
        )
        receptionist = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"reception_{clinic.id}@example.test",
            password_hash="test",
            full_name="Reception One",
            role=UserRole.RECEPTION.value,
            is_active=True,
        )
        db.add_all([doctor, receptionist])
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Patient A",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="08000000000",
            address="Test address",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        active_visit = Visit(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            assigned_doctor_id=doctor.id,
            status=VisitStatus.REGISTERED,
        )
        db.add(active_visit)
        db.commit()

        service = VisitService(db)
        payload = VisitCreateRequest(
            patient_id=patient.id,
            assigned_doctor_id=doctor.id,
        )

        with pytest.raises(HTTPException) as exc:
            service.start_visit(payload, receptionist)
        assert exc.value.status_code == 409
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_start_visit_allowed_after_completion():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Test Clinic")
        db.add(clinic)
        db.commit()

        doctor = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"doctor_{clinic.id}@example.test",
            password_hash="test",
            full_name="Doctor Two",
            role=UserRole.DOCTOR.value,
            is_active=True,
        )
        receptionist = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"reception_{clinic.id}@example.test",
            password_hash="test",
            full_name="Reception Two",
            role=UserRole.RECEPTION.value,
            is_active=True,
        )
        db.add_all([doctor, receptionist])
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Patient A",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="08000000000",
            address="Test address",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        completed_visit = Visit(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            assigned_doctor_id=doctor.id,
            status=VisitStatus.COMPLETED,
        )
        db.add(completed_visit)
        db.commit()

        service = VisitService(db)
        payload = VisitCreateRequest(
            patient_id=patient.id,
            assigned_doctor_id=doctor.id,
        )

        new_visit = service.start_visit(payload, receptionist)
        assert new_visit.id != completed_visit.id
        assert new_visit.status == VisitStatus.REGISTERED
    finally:
        db.close()
