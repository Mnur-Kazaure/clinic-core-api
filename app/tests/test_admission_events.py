import uuid
from datetime import datetime, timezone

from app.models.event_log import EventLog
from app.models.user import User
from app.models.patient import Patient
from app.models.ward import Ward
from app.models.bed import Bed
from app.shared.enums import (
    AdmissionType,
    AdmissionStatus,
    WardType,
    BedStatus,
    Gender,
    UserRole,
)
from app.services.admission_service import AdmissionService
from app.services.bed_service import BedService


def test_admission_bed_events(db, clinic_id):
    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Admission Patient",
        date_of_birth=datetime(2000, 1, 1).date(),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    ward = Ward(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Ward A",
        ward_type=WardType.GENERAL,
        active=True,
    )
    db.add(ward)
    db.commit()

    bed_a = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        ward_id=ward.id,
        bed_label="A1",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    bed_b = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        ward_id=ward.id,
        bed_label="A2",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    db.add_all([bed_a, bed_b])
    db.commit()

    admission_service = AdmissionService(db)
    admission = admission_service.create_admission(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        actor=admin,
    )

    bed_service = BedService(db)
    bed_service.assign_bed(
        admission_id=admission.id,
        bed_id=bed_a.id,
        actor=admin,
    )

    bed_service.transfer_bed(
        admission_id=admission.id,
        to_bed_id=bed_b.id,
        actor=admin,
        reason="ICU transfer",
    )

    admission_service.discharge_admission(
        admission_id=admission.id,
        actor=admin,
    )

    event_types = {
        e.event_type for e in db.query(EventLog).all()
    }
    assert "PATIENT_ADMITTED" in event_types
    assert "BED_ASSIGNED" in event_types
    assert "BED_TRANSFERRED" in event_types
    assert "PATIENT_DISCHARGED" in event_types
