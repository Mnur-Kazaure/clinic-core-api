import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.services.billing_service import BillingService
from app.shared.enums import (
    Gender,
    UserRole,
    VisitStatus,
    BillingReasonCode,
)


def test_billing_reversal_rules(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A", billing_currency="NGN")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Billing Admin",
        role=UserRole.CLINIC_ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Billing Patient",
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
        assigned_doctor_id=admin.id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()

    service = BillingService(db)
    charge = service.create_charge_for_visit(
        visit_id=visit.id,
        code=None,
        amount_minor=2000,
        description="Consultation charge",
        reason_code=BillingReasonCode.SERVICE,
        actor=admin,
    )

    reversal = service.reverse_entry(
        entry_id=charge.id,
        justification="Patient dispute reversal",
        reason_code=BillingReasonCode.REVERSAL,
        actor=admin,
    )
    assert reversal.amount_minor == -charge.amount_minor

    with pytest.raises(HTTPException):
        service.reverse_entry(
            entry_id=reversal.id,
            justification="Second reversal",
            reason_code=BillingReasonCode.REVERSAL,
            actor=admin,
        )
