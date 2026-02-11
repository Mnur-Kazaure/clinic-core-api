import json
import uuid
from datetime import date

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.event_log import EventLog
from app.services.pmr_service import PMRService
from app.shared.enums import Gender, PurposeOfUse, UserRole, VisitStatus


def test_pmr_access_logging_payload_fields(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
        role=UserRole.CLINIC_ADMIN,
        is_active=True,
    )
    db.add(admin)

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
        full_name="PMR Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.REGISTERED,
    )
    db.add(visit)
    db.commit()

    service = PMRService(db)
    service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=admin,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="PMR access for verification",
        break_glass=False,
    )

    event = (
        db.query(EventLog)
        .filter(EventLog.event_type == "ACCESS_LOGGED")
        .order_by(EventLog.created_at.desc())
        .first()
    )
    payload = json.loads(event.payload)
    assert payload["resource"] == "PMR"
    assert payload["patient_id_requested"] == str(patient.id)
    assert payload["patient_id_canonical"] == str(patient.id)
