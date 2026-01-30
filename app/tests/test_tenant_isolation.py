import uuid
import pytest
from datetime import date, datetime

from fastapi import HTTPException

from app.models.patient import Patient
from app.models.visit import Visit
from app.models.consultation import Consultation
from app.models.user import User
from app.models.clinic import Clinic
from app.shared.enums import VisitStatus, UserRole, Gender, RecordStatus
from app.services.visit.service import VisitService
from app.core.guards.consultation_guards import require_consultation_access_by_visit


def _seed_clinic(db, name):
    clinic = Clinic(id=uuid.uuid4(), name=name)
    db.add(clinic)
    db.commit()
    return clinic


def _seed_user(db, clinic_id, role, email):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=email,
        password_hash="test",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _seed_patient_visit_consultation(db, clinic_id, doctor_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Tenant Patient",
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
        assigned_doctor_id=doctor_id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        started_at=datetime(2026, 1, 1, 0, 0, 0),
        record_status=RecordStatus.DRAFT,
    )
    db.add(consultation)
    db.commit()
    return visit, consultation


def test_cross_tenant_visit_transition_denied(db):
    clinic_a = _seed_clinic(db, "Clinic A")
    clinic_b = _seed_clinic(db, "Clinic B")

    doctor_a = _seed_user(db, clinic_a.id, UserRole.DOCTOR, "a@a.test")
    doctor_b = _seed_user(db, clinic_b.id, UserRole.DOCTOR, "b@b.test")

    visit, _ = _seed_patient_visit_consultation(db, clinic_a.id, doctor_a.id)

    service = VisitService(db)
    with pytest.raises(HTTPException):
        service.transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.TRIAGED,
            user=doctor_b,
        )


def test_cross_tenant_consultation_read_denied(db):
    clinic_a = _seed_clinic(db, "Clinic A")
    clinic_b = _seed_clinic(db, "Clinic B")

    doctor_a = _seed_user(db, clinic_a.id, UserRole.DOCTOR, "a2@a.test")
    doctor_b = _seed_user(db, clinic_b.id, UserRole.DOCTOR, "b2@b.test")

    visit, consultation = _seed_patient_visit_consultation(
        db, clinic_a.id, doctor_a.id
    )

    with pytest.raises(HTTPException):
        require_consultation_access_by_visit(
            visit_id=visit.id,
            db=db,
            current_user=doctor_b,
        )
