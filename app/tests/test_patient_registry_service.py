from datetime import date
import uuid

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.patient import PatientCreateSchema
from app.services.patient_service import PatientService
from app.shared.enums import Gender, UserRole


def _create_clinic_and_reception(db):
    clinic = Clinic(id=uuid.uuid4(), name='Registry Clinic')
    db.add(clinic)
    db.commit()

    receptionist = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f'reception_{clinic.id}@example.test',
        password_hash='test',
        role=UserRole.RECEPTION,
        is_active=True,
    )
    db.add(receptionist)
    db.commit()
    return clinic, receptionist


def _payload(full_name: str):
    return PatientCreateSchema(
        full_name=full_name,
        date_of_birth=date(1995, 1, 1),
        gender=Gender.FEMALE,
        phone_number='08012345678',
        address='Main street',
        occupation='Business',
    )


def test_list_patients_returns_total_and_active_mrn(db):
    clinic, receptionist = _create_clinic_and_reception(db)
    service = PatientService(db)

    first = service.create_patient(_payload('Amina Yusuf'), receptionist)
    second = service.create_patient(_payload('Zainab Musa'), receptionist)

    result = service.list_patients(
        clinic_id=clinic.id,
        q=None,
        limit=10,
        offset=0,
    )

    assert result['total'] == 2
    assert len(result['items']) == 2
    returned_ids = {item.id for item in result['items']}
    assert returned_ids == {first.id, second.id}
    assert all(item.patient_mrn for item in result['items'])


def test_get_patient_is_clinic_scoped(db):
    clinic_a, receptionist_a = _create_clinic_and_reception(db)
    clinic_b, _ = _create_clinic_and_reception(db)
    service = PatientService(db)

    patient = service.create_patient(_payload('Scoped Patient'), receptionist_a)

    with pytest.raises(HTTPException) as exc:
        service.get_patient(clinic_id=clinic_b.id, patient_id=patient.id)

    assert exc.value.status_code == 404
