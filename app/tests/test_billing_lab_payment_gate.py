import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.billing_item import BillingItem
from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.lab_request import LabRequest
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_request_service import LabRequestService
from app.shared.enums import (
    BillingItemStatus,
    BillingReasonCode,
    Gender,
    UserRole,
    VisitStatus,
)


def _seed_context(db, clinic_id: uuid.UUID):
    clinic = Clinic(
        id=clinic_id,
        name="Billing Flow Clinic",
        billing_currency="NGN",
    )
    db.add(clinic)
    db.commit()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor-{clinic_id}@example.test",
        password_hash="test",
        full_name="Doctor One",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"cashier-{clinic_id}@example.test",
        password_hash="test",
        full_name="Cashier One",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    lab_user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-{clinic_id}@example.test",
        password_hash="test",
        full_name="Lab One",
        role=UserRole.LAB.value,
        is_active=True,
    )
    db.add_all([doctor, cashier, lab_user])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Jane Patient",
        date_of_birth=date(1995, 5, 10),
        gender=Gender.FEMALE,
        phone_number="08000000001",
        address="Test Address",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()
    return clinic, doctor, cashier, lab_user, patient, visit


def test_lab_request_creates_pending_billing_item_and_unpaid_hidden_from_lab_queue(db, clinic_id):
    clinic, doctor, cashier, _lab_user, _patient, visit = _seed_context(db, clinic_id)
    charge = ChargeCatalog(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        code="LAB_BLOOD_GLUCOSE_FASTING",
        name="Blood Glucose (Fasting)",
        category="LAB",
        default_amount_minor=100000,
        currency=clinic.billing_currency,
        active=True,
    )
    db.add(charge)
    db.commit()

    lab_request = LabRequestService(db).create_request(
        visit=visit,
        test_name="Blood Glucose (Fasting)",
        test_code="LAB_BLOOD_GLUCOSE_FASTING",
        doctor_id=doctor.id,
        actor=doctor,
    )

    billing_item = db.query(BillingItem).filter(BillingItem.id == lab_request.billing_item_id).first()
    assert billing_item is not None
    assert billing_item.status == BillingItemStatus.PENDING
    assert billing_item.total_minor == 100000
    assert BillingWorkflowService(db).is_lab_request_paid(lab_request=lab_request) is False

    paid_queue = (
        db.query(LabRequest)
        .join(Visit, LabRequest.visit_id == Visit.id)
        .join(BillingItem, BillingItem.id == LabRequest.billing_item_id)
        .filter(
            Visit.clinic_id == clinic.id,
            BillingItem.status == BillingItemStatus.PAID,
        )
        .all()
    )
    assert lab_request.id not in [request.id for request in paid_queue]

    BillingWorkflowService(db).start_shift(
        clinic_id=clinic.id,
        cashier_user=cashier,
        opening_float_minor=0,
    )

    BillingWorkflowService(db).pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[billing_item.id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )

    db.refresh(billing_item)
    assert billing_item.status == BillingItemStatus.PAID
    assert billing_item.amount_paid_minor == billing_item.total_minor

    paid_queue_after_payment = (
        db.query(LabRequest)
        .join(Visit, LabRequest.visit_id == Visit.id)
        .join(BillingItem, BillingItem.id == LabRequest.billing_item_id)
        .filter(
            Visit.clinic_id == clinic.id,
            BillingItem.status == BillingItemStatus.PAID,
        )
        .all()
    )
    assert lab_request.id in [request.id for request in paid_queue_after_payment]
    assert BillingWorkflowService(db).is_lab_request_paid(lab_request=lab_request) is True


def test_lab_request_creation_fails_when_lab_price_not_configured(db, clinic_id):
    _clinic, doctor, _cashier, _lab_user, _patient, visit = _seed_context(db, clinic_id)

    with pytest.raises(HTTPException) as exc:
        LabRequestService(db).create_request(
            visit=visit,
            test_name="Unavailable Priced Test",
            test_code=None,
            doctor_id=doctor.id,
            actor=doctor,
        )

    assert exc.value.status_code == 422
    assert "No active lab price configured" in str(exc.value.detail)
