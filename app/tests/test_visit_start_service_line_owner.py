import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.services.visit.service import VisitService
from app.shared.enums import Gender, UserRole, VisitServiceLine
from app.schemas.visit import VisitCreateRequest


def _make_user(db, *, clinic_id, role: UserRole, name: str):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"{role.value.lower()}.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name=name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _make_patient(db, *, clinic_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Patient A",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()
    return patient


def test_start_visit_validates_owner_role_by_service_line(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    reception = _make_user(db, clinic_id=clinic_id, role=UserRole.RECEPTION, name="Reception")
    doctor = _make_user(db, clinic_id=clinic_id, role=UserRole.DOCTOR, name="Doctor")
    chew = _make_user(db, clinic_id=clinic_id, role=UserRole.CHEW, name="CHEW")
    midwife = _make_user(db, clinic_id=clinic_id, role=UserRole.MIDWIFE, name="Midwife")

    service = VisitService(db)

    visit = service.start_visit(
        VisitCreateRequest(
            patient_id=_make_patient(db, clinic_id=clinic_id).id,
            assigned_doctor_id=doctor.id,
            service_line=VisitServiceLine.OPD,
        ),
        reception,
    )
    assert visit.service_line == VisitServiceLine.OPD

    visit = service.start_visit(
        VisitCreateRequest(
            patient_id=_make_patient(db, clinic_id=clinic_id).id,
            assigned_doctor_id=chew.id,
            service_line=VisitServiceLine.ANC,
        ),
        reception,
    )
    assert visit.service_line == VisitServiceLine.ANC

    visit = service.start_visit(
        VisitCreateRequest(
            patient_id=_make_patient(db, clinic_id=clinic_id).id,
            assigned_doctor_id=midwife.id,
            service_line=VisitServiceLine.MATERNITY,
        ),
        reception,
    )
    assert visit.service_line == VisitServiceLine.MATERNITY

    with pytest.raises(HTTPException) as excinfo:
        service.start_visit(
            VisitCreateRequest(
                patient_id=_make_patient(db, clinic_id=clinic_id).id,
                assigned_doctor_id=doctor.id,
                service_line=VisitServiceLine.ANC,
            ),
            reception,
        )
    assert excinfo.value.status_code == 404
