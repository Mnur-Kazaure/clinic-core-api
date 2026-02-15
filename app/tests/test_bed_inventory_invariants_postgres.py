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
from app.models.bed import Bed
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.services.admission_service import AdmissionService
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


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_mark_out_of_service_requires_unoccupied_bed():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Status Clinic")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin Status",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Bed Status Patient",
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
            name="Status Ward",
            ward_type=WardType.GENERAL,
        )
        bed = service.create_bed(
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="S-01",
            status_value=BedStatus.AVAILABLE,
        )
        service.assign_bed(
            admission_id=admission.id,
            bed_id=bed.id,
            actor=admin,
        )

        with pytest.raises(HTTPException) as occupied_exc:
            service.update_bed_status(
                clinic_id=clinic.id,
                bed_id=bed.id,
                status_value=BedStatus.OUT_OF_SERVICE,
                actor=admin,
                reason="Maintenance",
            )

        assert occupied_exc.value.status_code == 409
        assert occupied_exc.value.detail == "Cannot mark bed out of service while occupied"

        assignment = (
            db.query(BedAssignment)
            .filter(
                BedAssignment.bed_id == bed.id,
                BedAssignment.released_at.is_(None),
            )
            .first()
        )
        assignment.released_at = datetime.now(timezone.utc)
        db.commit()

        updated = service.update_bed_status(
            clinic_id=clinic.id,
            bed_id=bed.id,
            status_value=BedStatus.OUT_OF_SERVICE,
            actor=admin,
            reason="Maintenance",
        )
        assert updated.status == BedStatus.OUT_OF_SERVICE
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_manual_bed_release_requires_active_assignment_and_releases_when_present():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Release Clinic")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.release.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin Release",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Release Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.FEMALE,
            phone_number="08000000001",
            address="Test address",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        admission = Admission(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        db.add(admission)
        db.commit()

        admission_service = AdmissionService(db)
        with pytest.raises(HTTPException) as missing_exc:
            admission_service.release_admission_bed(
                admission_id=admission.id,
                actor=admin,
                reason="No bed yet",
            )
        assert missing_exc.value.status_code == 409
        assert missing_exc.value.detail == "No active bed assignment"

        bed_service = BedService(db)
        ward = bed_service.create_ward(
            clinic_id=clinic.id,
            name="Release Ward",
            ward_type=WardType.GENERAL,
        )
        bed = bed_service.create_bed(
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="R-01",
            status_value=BedStatus.AVAILABLE,
        )
        bed_service.assign_bed(
            admission_id=admission.id,
            bed_id=bed.id,
            actor=admin,
        )

        admission_service.release_admission_bed(
            admission_id=admission.id,
            actor=admin,
            reason="Moved to observation",
        )
        active_assignment = (
            db.query(BedAssignment)
            .filter(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .first()
        )
        assert active_assignment is None
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_cannot_deactivate_occupied_bed_or_ward():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Active Guard Clinic")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.guard.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin Guard",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Guard Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.FEMALE,
            phone_number="08000000002",
            address="Test address",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        admission = Admission(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        db.add(admission)
        db.commit()

        service = BedService(db)
        ward = service.create_ward(
            clinic_id=clinic.id,
            name="Guard Ward",
            ward_type=WardType.GENERAL,
        )
        bed = service.create_bed(
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="G-01",
            status_value=BedStatus.AVAILABLE,
        )
        service.assign_bed(
            admission_id=admission.id,
            bed_id=bed.id,
            actor=admin,
        )

        with pytest.raises(HTTPException) as bed_exc:
            service.set_bed_active(
                clinic_id=clinic.id,
                bed_id=bed.id,
                active=False,
                actor=admin,
                reason="Maintenance",
            )
        assert bed_exc.value.status_code == 409
        assert bed_exc.value.detail == "Cannot deactivate bed while occupied"

        with pytest.raises(HTTPException) as ward_exc:
            service.set_ward_active(
                clinic_id=clinic.id,
                ward_id=ward.id,
                active=False,
                actor=admin,
                reason="Ward shutdown",
            )
        assert ward_exc.value.status_code == 409
        assert ward_exc.value.detail == "Cannot deactivate ward while beds are occupied"
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_cannot_activate_bed_when_ward_is_inactive():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Reactivation Clinic")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.reactivate.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin Reactivate",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        service = BedService(db)
        ward = service.create_ward(
            clinic_id=clinic.id,
            name="Reactivate Ward",
            ward_type=WardType.GENERAL,
        )
        bed = service.create_bed(
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="R-10",
            status_value=BedStatus.AVAILABLE,
        )

        service.set_bed_active(
            clinic_id=clinic.id,
            bed_id=bed.id,
            active=False,
            actor=admin,
            reason="Temporarily closed",
        )
        service.set_ward_active(
            clinic_id=clinic.id,
            ward_id=ward.id,
            active=False,
            actor=admin,
            reason="Ward closed",
        )

        with pytest.raises(HTTPException) as exc:
            service.set_bed_active(
                clinic_id=clinic.id,
                bed_id=bed.id,
                active=True,
                actor=admin,
            )

        assert exc.value.status_code == 409
        assert exc.value.detail == "Cannot activate bed in inactive ward"
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_bed_range_preview_conflict_when_ward_name_exists():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Range Preview Clinic")
        db.add(clinic)
        db.commit()

        service = BedService(db)
        service.create_ward(
            clinic_id=clinic.id,
            name="Range Ward",
            ward_type=WardType.GENERAL,
        )

        preview = service.preview_ward_bed_range(
            clinic_id=clinic.id,
            payload=type("Payload", (), {
                "name": "Range Ward",
                "ward_type": WardType.GENERAL,
                "label_prefix": "A-",
                "label_from": 1,
                "label_to": 3,
                "label_padding": 2,
            })(),
        )

        assert preview.is_valid is False
        assert "WARD_NAME_EXISTS" in preview.conflicts
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_bed_range_commit_creates_labels_and_next_sequence():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Range Commit Clinic")
        db.add(clinic)
        db.commit()

        service = BedService(db)
        payload = type("Payload", (), {
            "name": "Male Ward",
            "ward_type": WardType.GENERAL,
            "label_prefix": "M-",
            "label_from": 1,
            "label_to": 3,
            "label_padding": 2,
        })()

        commit = service.create_ward_with_bed_range(
            clinic_id=clinic.id,
            payload=payload,
        )

        assert commit.created_beds == 3
        assert commit.ward.bed_label_prefix == "M-"
        assert commit.ward.bed_label_padding == 2
        assert commit.ward.bed_label_next == 4

        labels = {bed.bed_label for bed in db.query(Bed).filter(Bed.ward_id == commit.ward.id)}
        assert labels == {"M-01", "M-02", "M-03"}
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_bed_range_append_and_retire_last_bed():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Bed Range Append Clinic")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.range.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin Range",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        service = BedService(db)
        payload = type("Payload", (), {
            "name": "Female Ward",
            "ward_type": WardType.GENERAL,
            "label_prefix": "F-",
            "label_from": 1,
            "label_to": 2,
            "label_padding": 2,
        })()
        commit = service.create_ward_with_bed_range(clinic_id=clinic.id, payload=payload)

        appended = service.append_next_bed(
            clinic_id=clinic.id,
            ward_id=commit.ward.id,
            actor=admin,
        )
        assert appended.bed_label == "F-03"

        retired = service.retire_last_bed(
            clinic_id=clinic.id,
            ward_id=commit.ward.id,
            actor=admin,
            reason="Capacity reduction",
        )
        assert retired.bed_label == "F-03"

        bed = db.query(Bed).filter(Bed.id == retired.bed_id).first()
        assert bed is not None
        assert bed.active is False
    finally:
        db.close()
