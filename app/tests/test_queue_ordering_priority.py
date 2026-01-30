import uuid
from datetime import datetime, timezone, timedelta, date

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.services.visit.service import VisitService
from app.shared.enums import (
    VisitStatus,
    Gender,
    UserRole,
    ClinicalPriorityLevel,
    ClinicalPrioritySource,
)


def test_queue_ordering_by_priority_and_triage(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doc.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db.add(doctor)
    db.commit()

    def make_patient(name):
        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            full_name=name,
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()
        return patient

    now = datetime.now(timezone.utc)

    patient_a = make_patient("Patient A")
    patient_b = make_patient("Patient B")
    patient_c = make_patient("Patient C")

    visit_a = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_a.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.TRIAGED,
        started_at=now + timedelta(minutes=1),
    )
    visit_b = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_b.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.TRIAGED,
        started_at=now,
    )
    visit_c = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_c.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.REGISTERED,
        started_at=now + timedelta(minutes=2),
    )
    visit_d = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_c.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.COMPLETED,
        started_at=now + timedelta(minutes=3),
    )
    visit_e = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_c.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.CANCELLED,
        started_at=now + timedelta(minutes=4),
    )
    db.add_all([visit_a, visit_b, visit_c, visit_d, visit_e])
    db.commit()

    db.add_all(
        [
            VisitStatusHistory(
                id=uuid.uuid4(),
                visit_id=visit_a.id,
                from_status=VisitStatus.REGISTERED,
                to_status=VisitStatus.TRIAGED,
                changed_by=doctor.id,
                created_at=now + timedelta(minutes=1),
            ),
            VisitStatusHistory(
                id=uuid.uuid4(),
                visit_id=visit_b.id,
                from_status=VisitStatus.REGISTERED,
                to_status=VisitStatus.TRIAGED,
                changed_by=doctor.id,
                created_at=now,
            ),
        ]
    )
    db.commit()

    db.add_all(
        [
            ClinicalPriorityEvent(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                visit_id=visit_a.id,
                patient_id=patient_a.id,
                level=ClinicalPriorityLevel.URGENT,
                source=ClinicalPrioritySource.CLINICIAN,
                reason="urgent review",
                set_by=doctor.id,
                set_at=now + timedelta(minutes=2),
            ),
            ClinicalPriorityEvent(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                visit_id=visit_b.id,
                patient_id=patient_b.id,
                level=ClinicalPriorityLevel.CRITICAL,
                source=ClinicalPrioritySource.CLINICIAN,
                reason="critical",
                set_by=doctor.id,
                set_at=now + timedelta(minutes=2),
            ),
        ]
    )
    db.commit()

    service = VisitService(db)
    ordered = service.get_queue_for_doctor(
        clinic_id=clinic_id,
        doctor_id=doctor.id,
    )

    assert [visit.id for visit in ordered] == [
        visit_b.id,  # CRITICAL
        visit_a.id,  # URGENT
        visit_c.id,  # ROUTINE default
    ]
    assert visit_d.id not in [visit.id for visit in ordered]
    assert visit_e.id not in [visit.id for visit in ordered]
