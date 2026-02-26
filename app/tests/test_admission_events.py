import json
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
    bed_service.update_bed_status(
        clinic_id=clinic_id,
        bed_id=bed_a.id,
        status_value=BedStatus.OUT_OF_SERVICE,
        actor=admin,
        reason="Maintenance",
    )
    admission_service.release_admission_bed(
        admission_id=admission.id,
        actor=admin,
        reason="Moved to procedure room",
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
    assert "BED_STATUS_CHANGED" in event_types
    assert "BED_RELEASED" in event_types
    assert "PATIENT_DISCHARGED" in event_types


def test_bed_status_noop_is_audited(db, clinic_id):
    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.noop.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    ward = Ward(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Ward Noop",
        ward_type=WardType.GENERAL,
        active=True,
    )
    db.add(ward)
    db.commit()

    bed = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        ward_id=ward.id,
        bed_label="N1",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    db.add(bed)
    db.commit()

    service = BedService(db)
    service.update_bed_status(
        clinic_id=clinic_id,
        bed_id=bed.id,
        status_value=BedStatus.OUT_OF_SERVICE,
        actor=admin,
        reason="Maintenance",
    )
    service.update_bed_status(
        clinic_id=clinic_id,
        bed_id=bed.id,
        status_value=BedStatus.OUT_OF_SERVICE,
        actor=admin,
    )

    events = (
        db.query(EventLog)
        .filter(
            EventLog.event_type == "BED_STATUS_CHANGED",
            EventLog.clinic_id == clinic_id,
        )
        .order_by(EventLog.created_at.asc())
        .all()
    )
    target_events = [
        event
        for event in events
        if json.loads(event.payload).get("bed_id") == str(bed.id)
    ]
    assert len(target_events) == 2
    first_payload = json.loads(target_events[0].payload)
    second_payload = json.loads(target_events[1].payload)
    assert first_payload["no_op"] is False
    assert second_payload["no_op"] is True
