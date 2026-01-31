import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.charge_catalog import ChargeCatalog
from app.services.billing_service import BillingService
from app.shared.enums import Gender, UserRole, VisitStatus, BillingReasonCode


def test_billing_currency_enforced(db, clinic_id):
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

    catalog = ChargeCatalog(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code="XRAY",
        name="X-Ray",
        default_amount_minor=5000,
        currency="USD",
        active=True,
    )
    db.add(catalog)
    db.commit()

    service = BillingService(db)
    with pytest.raises(HTTPException):
        service.create_charge_for_visit(
            visit_id=visit.id,
            code="XRAY",
            amount_minor=None,
            description="X-Ray charge",
            reason_code=BillingReasonCode.PROCEDURE,
            actor=admin,
        )
