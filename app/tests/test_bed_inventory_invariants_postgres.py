import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.admission import Admission
from app.models.bed_assignment import BedAssignment
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.services.bed_service import BedService
from app.shared.enums import AdmissionStatus, AdmissionType, BedStatus, Gender, WardType


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


def _migrate(db_url: str) -> None:
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_create_ward_duplicate_name_returns_409():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Ward Duplicate Clinic")
        db.add(clinic)
        db.commit()

        service = BedService(db)
        service.create_ward(
            clinic_id=clinic.id,
            name="Male Ward",
            ward_type=WardType.GENERAL,
        )

        with pytest.raises(HTTPException) as exc:
            service.create_ward(
                clinic_id=clinic.id,
                name="Male Ward",
                ward_type=WardType.GENERAL,
            )

        assert exc.value.status_code == 409
        assert exc.value.detail == "Ward name already exists in clinic"
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_create_bed_duplicate_label_in_same_ward_returns_409():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Duplicate Clinic")
        db.add(clinic)
        db.commit()

        service = BedService(db)
        ward = service.create_ward(
            clinic_id=clinic.id,
            name="Female Ward",
            ward_type=WardType.GENERAL,
        )
        service.create_bed(
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="F-01",
            status_value=BedStatus.AVAILABLE,
        )

        with pytest.raises(HTTPException) as exc:
            service.create_bed(
                clinic_id=clinic.id,
                ward_id=ward.id,
                bed_label="F-01",
                status_value=BedStatus.AVAILABLE,
            )

        assert exc.value.status_code == 409
        assert exc.value.detail == "Bed label already exists in ward"
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_transfer_to_same_bed_returns_409_and_preserves_active_assignment():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Transfer Guard Clinic")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin Transfer",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Bed Transfer Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="08000000000",
            address="Test address",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        admission = Admission(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            admission_type=AdmissionType.ELECTIVE,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        db.add(admission)
        db.commit()

        service = BedService(db)
        ward = service.create_ward(
            clinic_id=clinic.id,
            name="Labour Ward",
            ward_type=WardType.MATERNITY,
        )
        bed = service.create_bed(
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="L-01",
            status_value=BedStatus.AVAILABLE,
        )
        service.assign_bed(
            admission_id=admission.id,
            bed_id=bed.id,
            actor=admin,
        )

        with pytest.raises(HTTPException) as exc:
            service.transfer_bed(
                admission_id=admission.id,
                to_bed_id=bed.id,
                actor=admin,
                reason="Move closer to nursing station",
            )

        assert exc.value.status_code == 409
        assert exc.value.detail == "Transfer target must differ from current bed"

        active = (
            db.query(BedAssignment)
            .filter(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .all()
        )
        assert len(active) == 1
        assert active[0].bed_id == bed.id
    finally:
        db.close()
