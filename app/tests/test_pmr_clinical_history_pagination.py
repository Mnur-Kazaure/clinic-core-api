import uuid
from datetime import date, datetime, timezone

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.services.pmr_service import PMRService
from app.shared.enums import Gender, PurposeOfUse, UserRole, VisitStatus


def test_pmr_clinical_history_paginates_visits_deterministically(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    reception = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"reception.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Reception",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Doctor",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db.add_all([reception, doctor])
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

    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 10, 0, 0, tzinfo=timezone.utc)

    visit_newer = Visit(
        id=uuid.UUID(int=2),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.REGISTERED,
        started_at=t2,
    )
    visit_older = Visit(
        id=uuid.UUID(int=1),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.REGISTERED,
        started_at=t1,
    )
    db.add_all([visit_older, visit_newer])
    db.commit()

    service = PMRService(db)
    page1 = service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="PMR lookup",
        break_glass=False,
        limit=1,
    )

    assert page1["clinical_history_page"]["has_more"] is True
    assert page1["clinical_history_page"]["next_cursor"]
    assert page1["clinical_history"][0]["visit_id"] == visit_newer.id

    page2 = service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="PMR lookup",
        break_glass=False,
        limit=1,
        cursor=page1["clinical_history_page"]["next_cursor"],
    )

    assert page2["clinical_history"][0]["visit_id"] == visit_older.id
    assert page2["clinical_history_page"]["has_more"] is False
    assert page2["clinical_history_page"]["next_cursor"] is None

