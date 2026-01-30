import json
import uuid
from datetime import datetime

from app.models.access_log import AccessLog
from app.models.event_log import EventLog
from app.models.user import User
from app.models.patient import Patient
from app.shared.enums import Gender, UserRole, PurposeOfUse
from app.services.access_log_service import AccessLogService


def test_break_glass_dual_logging(db, clinic_id):
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Doctor",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db.add(doctor)
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Break Glass Patient",
        date_of_birth=datetime(2000, 1, 1).date(),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    service = AccessLogService(db)
    service.log_break_glass(
        actor=doctor,
        clinic_id=clinic_id,
        patient_id=patient.id,
        purpose_of_use=PurposeOfUse.EMERGENCY,
        justification="Unresponsive patient",
        resource="PATIENT_CHART",
    )

    access_log = db.query(AccessLog).filter(AccessLog.action == "BREAK_GLASS").first()
    assert access_log is not None
    assert access_log.break_glass is True

    event = db.query(EventLog).filter(EventLog.event_type == "BREAK_GLASS_USED").first()
    assert event is not None
    payload = json.loads(event.payload)
    assert payload["access_log_id"] == str(access_log.id)
