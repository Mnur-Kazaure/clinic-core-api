import uuid
from datetime import datetime

from app.models.user import User
from app.models.patient import Patient
from app.models.admission_visit_link import AdmissionVisitLink
from app.shared.enums import AdmissionType, Gender, UserRole
from app.services.admission_service import AdmissionService
from app.services.visit.service import VisitService
from app.schemas.visit import VisitCreateRequest


def test_admission_visit_link_auto_created(db, clinic_id):
    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    db.add_all([admin, doctor])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Admission Link Patient",
        date_of_birth=datetime(2000, 1, 1).date(),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    AdmissionService(db).create_admission(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        actor=admin,
    )

    payload = VisitCreateRequest(
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
    )
    VisitService(db).start_visit(payload, doctor)

    link = (
        db.query(AdmissionVisitLink)
        .filter(AdmissionVisitLink.visit_id.isnot(None))
        .first()
    )
    assert link is not None
    assert link.visit_id is not None
    assert link.admission_id is not None
