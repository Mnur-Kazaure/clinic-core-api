import uuid
from datetime import datetime

from app.models.access_log import AccessLog
from app.models.event_log import EventLog
from app.models.user import User
from app.models.patient import Patient
from app.shared.enums import AdmissionType, Gender, UserRole
from app.services.admission_service import AdmissionService


def test_break_glass_dual_logging(db, clinic_id):
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
        full_name="Break Glass Patient",
        date_of_birth=datetime(2000, 1, 1).date(),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    service = AdmissionService(db)
    service.create_admission(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        actor=admin,
        break_glass=True,
        purpose_of_use="EMERGENCY_CARE",
        reason="Unresponsive patient",
    )

    access_log = db.query(AccessLog).filter(AccessLog.action == "BREAK_GLASS").first()
    assert access_log is not None
    assert access_log.break_glass is True

    event_types = {e.event_type for e in db.query(EventLog).all()}
    assert "BREAK_GLASS_USED" in event_types
    assert "ACCESS_LOGGED" in event_types
