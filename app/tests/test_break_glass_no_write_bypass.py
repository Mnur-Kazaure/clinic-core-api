import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.services.admission_service import AdmissionService
from app.shared.enums import AdmissionType, Gender, UserRole


def test_break_glass_rejected_on_write(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.CLINIC_ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Write Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    service = AdmissionService(db)
    with pytest.raises(HTTPException):
        service.create_admission(
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            actor=admin,
            break_glass=True,
            purpose_of_use="EMERGENCY",
            reason="not allowed",
        )
