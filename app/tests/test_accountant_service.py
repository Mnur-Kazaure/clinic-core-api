import uuid
from datetime import date, datetime, timedelta, timezone

from app.models.billing_item import BillingItem
from app.models.billing_refund import BillingRefund
from app.models.cashier_shift import CashierShift
from app.models.clinic import Clinic
from app.models.department import Department
from app.models.patient import Patient
from app.models.payment_receipt import PaymentReceipt
from app.models.receipt_reprint_log import ReceiptReprintLog
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.accountant_service import AccountantService
from app.shared.enums import BillingItemStatus, BillingReasonCode, Gender, UserRole, VisitStatus


def _seed_finance_context(db, clinic_id: uuid.UUID):
    clinic = Clinic(
        id=clinic_id,
        name="Specialist Hospital Kazaure",
        billing_currency="NGN",
    )
    db.add(clinic)
    db.commit()

    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"cashier-{clinic_id}@example.test",
        password_hash="test",
        full_name="Cashier Amina",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    accountant = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"accountant-{clinic_id}@example.test",
        password_hash="test",
        full_name="Accountant Fatima",
        role=UserRole.ACCOUNTANT.value,
        is_active=True,
    )
    clinic_admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin-{clinic_id}@example.test",
        password_hash="test",
        full_name="Finance Manager",
        role=UserRole.CLINIC_ADMIN.value,
        is_active=True,
    )
    db.add_all([cashier, accountant, clinic_admin])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Abba Nura",
        date_of_birth=date(1992, 1, 1),
        gender=Gender.MALE,
        phone_number="08010000000",
        address="Kazaure",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    department_gopd = Department(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="GOPD",
    )
    db.add(department_gopd)
    db.commit()

    gopd = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="GOPD",
        parent_id=None,
        department_id=department_gopd.id,
        requires_doctor=True,
        is_active=True,
    )
    consultation = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Consultation",
        parent_id=gopd.id,
        department_id=None,
        requires_doctor=True,
        is_active=True,
    )
    db.add_all([gopd, consultation])
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=None,
        status=VisitStatus.IN_CONSULTATION,
        service_line_id=consultation.id,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    now = datetime.now(timezone.utc)
    receipt_1 = PaymentReceipt(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        visit_id=visit.id,
        receipt_number="RCPT-100001",
        total_amount_minor=200_000,
        currency="NGN",
        payment_method=BillingReasonCode.CASH,
        external_ref=None,
        notes="Cash collection",
        collected_by=cashier.id,
        occurred_at=now - timedelta(hours=2),
    )
    receipt_2 = PaymentReceipt(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        visit_id=visit.id,
        receipt_number="RCPT-100002",
        total_amount_minor=150_000,
        currency="NGN",
        payment_method=BillingReasonCode.CARD,
        external_ref="POS-123",
        notes="POS collection",
        collected_by=cashier.id,
        occurred_at=now - timedelta(hours=1),
    )
    db.add_all([receipt_1, receipt_2])
    db.commit()

    outstanding_item = BillingItem(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        visit_id=visit.id,
        charge_catalog_id=None,
        charge_code="LAB_HBV",
        item_name="HBV Screen",
        service_type="LAB_TEST",
        quantity=1,
        unit_price_minor=100_000,
        total_minor=100_000,
        amount_paid_minor=20_000,
        currency="NGN",
        status=BillingItemStatus.PENDING,
        created_by=cashier.id,
        payment_reference=None,
        paid_at=None,
    )
    db.add(outstanding_item)
    db.commit()

    refund = BillingRefund(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        receipt_id=receipt_2.id,
        billing_item_id=outstanding_item.id,
        amount_minor=50_000,
        currency="NGN",
        reason="Duplicate payment",
        status="PROCESSED",
        requested_by=accountant.id,
        approved_by=clinic_admin.id,
        processed_by=cashier.id,
        requested_at=now - timedelta(minutes=50),
        processed_at=now - timedelta(minutes=45),
        notes="Validated",
    )
    db.add(refund)
    db.commit()

    shift = CashierShift(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        cashier_id=cashier.id,
        status="CLOSED",
        started_at=now - timedelta(hours=8),
        ended_at=now - timedelta(minutes=10),
        opening_float_minor=0,
        closing_cash_minor=300_000,
        closing_note="Pending reconciliation",
    )
    db.add(shift)
    db.commit()

    reprint = ReceiptReprintLog(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        receipt_id=receipt_1.id,
        reprinted_by=cashier.id,
        reason="Patient misplaced copy",
        reprinted_at=now - timedelta(minutes=5),
    )
    db.add(reprint)
    db.commit()

    return {
        "clinic": clinic,
        "cashier": cashier,
        "accountant": accountant,
        "clinic_admin": clinic_admin,
        "patient": patient,
        "visit": visit,
        "receipt_1": receipt_1,
        "receipt_2": receipt_2,
        "shift": shift,
    }


def test_accountant_overview_breakdowns_and_outstanding(db, clinic_id):
    ctx = _seed_finance_context(db, clinic_id)
    service = AccountantService(db)
    target_date = datetime.now(timezone.utc).date()

    overview = service.get_overview(clinic_id=ctx["clinic"].id, for_date=target_date)
    assert overview["currency"] == "NGN"
    assert overview["revenue_today_minor"] == 350_000
    assert overview["revenue_this_month_minor"] >= overview["revenue_today_minor"]
    assert overview["outstanding_bills_minor"] == 80_000
    assert overview["refunds_today_minor"] == 50_000

    dept_rows = service.list_revenue_by_department(
        clinic_id=ctx["clinic"].id,
        start_date=target_date,
        end_date=target_date,
    )
    assert len(dept_rows) >= 1
    assert any(row["department_name"] == "GOPD" for row in dept_rows)

    method_rows = service.list_payment_methods(
        clinic_id=ctx["clinic"].id,
        start_date=target_date,
        end_date=target_date,
    )
    assert len(method_rows) == 2
    assert {row["payment_method"] for row in method_rows} == {
        BillingReasonCode.CASH,
        BillingReasonCode.CARD,
    }

    outstanding = service.list_outstanding_bills(
        clinic_id=ctx["clinic"].id,
        limit=10,
        offset=0,
    )
    assert outstanding["total"] == 1
    assert outstanding["data"][0]["outstanding_minor"] == 80_000


def test_accountant_sessions_audit_signals_and_reconcile_idempotent(db, clinic_id):
    ctx = _seed_finance_context(db, clinic_id)
    service = AccountantService(db)
    target_date = datetime.now(timezone.utc).date()

    sessions = service.list_cashier_sessions(
        clinic_id=ctx["clinic"].id,
        limit=10,
        offset=0,
    )
    assert sessions["total"] == 1
    first_session = sessions["data"][0]
    assert first_session["expected_total_minor"] == 350_000
    assert first_session["variance_minor"] == 50_000

    detail = service.get_cashier_session_detail(
        clinic_id=ctx["clinic"].id,
        session_id=ctx["shift"].id,
    )
    assert detail["payments_total_minor"] == 350_000
    assert detail["refunds_total_minor"] == 50_000
    assert len(detail["transactions"]) >= 3

    refunds = service.list_refunds(
        clinic_id=ctx["clinic"].id,
        start_date=target_date,
        end_date=target_date,
        limit=10,
        offset=0,
    )
    assert refunds["total"] == 1
    assert refunds["data"][0]["amount_minor"] == 50_000

    refund_reasons = service.list_refund_reasons(clinic_id=ctx["clinic"].id)
    assert len(refund_reasons) >= 4
    assert any(reason["reason_code"] == "DUPLICATE" for reason in refund_reasons)

    feed = service.get_audit_feed(clinic_id=ctx["clinic"].id, limit=50, offset=0)
    event_types = {item["event_type"] for item in feed["data"]}
    assert "PAYMENT_POSTED" in event_types
    assert "REFUND_ISSUED" in event_types
    assert "RECEIPT_REPRINTED" in event_types
    assert "SHIFT_CLOSED" in event_types

    signals = service.get_fraud_signals(clinic_id=ctx["clinic"].id, for_date=target_date)
    assert signals["large_refunds_count"] == 0
    assert signals["reprints_today_count"] == 1
    assert signals["open_variances_count"] == 1
    assert signals["cash_total_today_minor"] == 200_000

    key = "reconcile-key-001"
    response_a = service.reconcile_cashier_session(
        clinic_id=ctx["clinic"].id,
        session_id=ctx["shift"].id,
        actor=ctx["clinic_admin"],
        idempotency_key=key,
        counted_total_minor=350_000,
        closing_note="Finance manager reconciliation",
    )
    response_b = service.reconcile_cashier_session(
        clinic_id=ctx["clinic"].id,
        session_id=ctx["shift"].id,
        actor=ctx["clinic_admin"],
        idempotency_key=key,
        counted_total_minor=350_000,
        closing_note="Finance manager reconciliation",
    )
    assert response_a["status"] == "RECONCILED"
    assert response_b["session_id"] == response_a["session_id"]
    assert response_b["reconciled_at"] == response_a["reconciled_at"]
