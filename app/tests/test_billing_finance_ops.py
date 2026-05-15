import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.billing_item import BillingItem
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.billing_refund import BillingRefund
from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.payment_receipt import PaymentReceipt
from app.models.receipt_sequence import ReceiptSequence
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_request_service import LabRequestService
from app.shared.enums import (
    BillingEntryType,
    BillingItemStatus,
    BillingReasonCode,
    Gender,
    UserRole,
    VisitStatus,
)


def _seed_context(db, clinic_id: uuid.UUID):
    clinic = Clinic(
        id=clinic_id,
        name="Finance Ops Clinic",
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
    accountant = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"accountant-{clinic_id}@example.test",
        password_hash="test",
        full_name="Accountant One",
        role=UserRole.ACCOUNTANT.value,
        is_active=True,
    )
    db.add_all([doctor, cashier, accountant])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Jane Finance",
        date_of_birth=date(1994, 6, 2),
        gender=Gender.FEMALE,
        phone_number="08000000011",
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

    return clinic, doctor, cashier, accountant, patient, visit


def _seed_lab_charge(db, clinic_id: uuid.UUID, code: str, name: str, amount_minor: int) -> None:
    db.add(
        ChargeCatalog(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            code=code,
            name=name,
            category="LAB",
            default_amount_minor=amount_minor,
            currency="NGN",
            active=True,
        )
    )
    db.commit()


def test_cashier_payment_requires_open_shift(db, clinic_id):
    clinic, doctor, cashier, _accountant, _patient, visit = _seed_context(db, clinic_id)
    _seed_lab_charge(
        db,
        clinic.id,
        code="LAB_CBC",
        name="Complete Blood Count",
        amount_minor=55000,
    )

    lab_request = LabRequestService(db).create_request(
        visit=visit,
        test_name="Complete Blood Count",
        test_code="LAB_CBC",
        doctor_id=doctor.id,
        actor=doctor,
    )
    billing_item = db.query(BillingItem).filter(BillingItem.id == lab_request.billing_item_id).first()
    assert billing_item is not None

    with pytest.raises(HTTPException) as exc:
        BillingWorkflowService(db).pay_billing_items(
            clinic_id=clinic.id,
            visit_id=visit.id,
            billing_item_ids=[billing_item.id],
            payment_method=BillingReasonCode.CASH,
            cashier_user=cashier,
        )
    assert exc.value.status_code == 409
    assert "active cashier shift" in str(exc.value.detail)

    BillingWorkflowService(db).start_shift(
        clinic_id=clinic.id,
        cashier_user=cashier,
        opening_float_minor=0,
    )
    payment = BillingWorkflowService(db).pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[billing_item.id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )
    assert payment["receipt_number"] == "RCPT-000001"


def test_receipt_numbers_are_gapless_per_clinic(db, clinic_id):
    clinic, doctor, cashier, _accountant, _patient, visit = _seed_context(db, clinic_id)
    _seed_lab_charge(db, clinic.id, code="LAB_MALARIA", name="Malaria Test", amount_minor=35000)
    _seed_lab_charge(db, clinic.id, code="LAB_URINE", name="Urinalysis", amount_minor=25000)

    first = LabRequestService(db).create_request(
        visit=visit,
        test_name="Malaria Test",
        test_code="LAB_MALARIA",
        doctor_id=doctor.id,
        actor=doctor,
    )
    second = LabRequestService(db).create_request(
        visit=visit,
        test_name="Urinalysis",
        test_code="LAB_URINE",
        doctor_id=doctor.id,
        actor=doctor,
    )

    BillingWorkflowService(db).start_shift(
        clinic_id=clinic.id,
        cashier_user=cashier,
        opening_float_minor=0,
    )

    first_payment = BillingWorkflowService(db).pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[first.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )
    second_payment = BillingWorkflowService(db).pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[second.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )

    assert first_payment["receipt_number"] == "RCPT-000001"
    assert second_payment["receipt_number"] == "RCPT-000002"

    sequence = (
        db.query(ReceiptSequence)
        .filter(ReceiptSequence.clinic_id == clinic.id)
        .one()
    )
    assert sequence.last_number == 2

    receipts = db.query(PaymentReceipt).filter(PaymentReceipt.clinic_id == clinic.id).all()
    assert len(receipts) == 2


def test_refund_marks_item_refunded_and_writes_ledger(db, clinic_id):
    clinic, doctor, cashier, accountant, _patient, visit = _seed_context(db, clinic_id)
    _seed_lab_charge(
        db,
        clinic.id,
        code="LAB_ELECTROLYTES",
        name="Electrolytes Panel",
        amount_minor=120000,
    )

    lab_request = LabRequestService(db).create_request(
        visit=visit,
        test_name="Electrolytes Panel",
        test_code="LAB_ELECTROLYTES",
        doctor_id=doctor.id,
        actor=doctor,
    )

    BillingWorkflowService(db).start_shift(
        clinic_id=clinic.id,
        cashier_user=cashier,
        opening_float_minor=0,
    )
    payment = BillingWorkflowService(db).pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[lab_request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )

    refund = BillingWorkflowService(db).process_refund(
        clinic_id=clinic.id,
        receipt_id=payment["receipt_id"],
        actor=accountant,
        reason="Service cancelled",
    )
    assert refund["status"] == "PROCESSED"
    assert refund["amount_minor"] == 120000

    item = db.query(BillingItem).filter(BillingItem.id == lab_request.billing_item_id).one()
    assert item.status == BillingItemStatus.REFUNDED
    assert item.amount_paid_minor == 0
    assert item.paid_at is None

    refund_rows = db.query(BillingRefund).filter(BillingRefund.receipt_id == payment["receipt_id"]).all()
    assert len(refund_rows) == 1
    assert refund_rows[0].amount_minor == 120000

    refund_ledger = (
        db.query(BillingLedgerEntry)
        .filter(
            BillingLedgerEntry.clinic_id == clinic.id,
            BillingLedgerEntry.visit_id == visit.id,
            BillingLedgerEntry.entry_type == BillingEntryType.REFUND,
        )
        .all()
    )
    assert len(refund_ledger) == 1
    assert refund_ledger[0].amount_minor == 120000


def test_list_transactions_supports_method_and_date_filters(db, clinic_id):
    clinic, doctor, cashier, _accountant, _patient, visit = _seed_context(db, clinic_id)
    _seed_lab_charge(db, clinic.id, code="LAB_HBV", name="HBV Screen", amount_minor=50000)
    _seed_lab_charge(db, clinic.id, code="LAB_WIDAL", name="Widal Test", amount_minor=75000)

    first = LabRequestService(db).create_request(
        visit=visit,
        test_name="HBV Screen",
        test_code="LAB_HBV",
        doctor_id=doctor.id,
        actor=doctor,
    )
    second = LabRequestService(db).create_request(
        visit=visit,
        test_name="Widal Test",
        test_code="LAB_WIDAL",
        doctor_id=doctor.id,
        actor=doctor,
    )

    service = BillingWorkflowService(db)
    service.start_shift(
        clinic_id=clinic.id,
        cashier_user=cashier,
        opening_float_minor=0,
    )

    cash_payment = service.pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[first.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )
    transfer_payment = service.pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[second.billing_item_id],
        payment_method=BillingReasonCode.TRANSFER,
        cashier_user=cashier,
        external_ref="TX-12345",
    )

    older_receipt = (
        db.query(PaymentReceipt)
        .filter(PaymentReceipt.id == cash_payment["receipt_id"])
        .one()
    )
    older_receipt.occurred_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.add(older_receipt)
    db.commit()

    today = date.today()

    today_rows = service.list_transactions(
        clinic_id=clinic.id,
        start_date=today,
        end_date=today,
        page=1,
        limit=25,
    )
    assert today_rows["total"] == 1
    assert today_rows["total_amount_minor"] == 75000
    assert today_rows["data"][0]["receipt_id"] == transfer_payment["receipt_id"]

    transfer_rows = service.list_transactions(
        clinic_id=clinic.id,
        payment_method=BillingReasonCode.TRANSFER,
        page=1,
        limit=25,
    )
    assert transfer_rows["total"] == 1
    assert transfer_rows["total_amount_minor"] == 75000
    assert transfer_rows["data"][0]["payment_method"] == BillingReasonCode.TRANSFER

    cash_rows = service.list_transactions(
        clinic_id=clinic.id,
        payment_method=BillingReasonCode.CASH,
        page=1,
        limit=25,
    )
    assert cash_rows["total"] == 1
    assert cash_rows["total_amount_minor"] == 50000
    assert cash_rows["data"][0]["receipt_id"] == cash_payment["receipt_id"]
