from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.models.billing_item import BillingItem
from app.models.patient_mrn import PatientMRN
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.cashier_dashboard_service import CashierDashboardService
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.prescription_service import PrescriptionService
from app.shared.enums import BillingItemStatus, BillingReasonCode, MRNStatus, UserRole
from app.tests.test_pharmacy_enterprise_workflow import _seed_core_context


def _seed_active_mrn(db, ctx):
    db.add(
        PatientMRN(
            id=uuid.uuid4(),
            clinic_id=ctx["clinic"].id,
            patient_id=ctx["patient"].id,
            mrn="KH-0000001-1",
            status=MRNStatus.ACTIVE,
            issued_at=datetime.now(timezone.utc),
            issued_by=ctx["doctor"].id,
            check_digit="1",
        )
    )
    db.commit()


def test_cashier_dashboard_separates_pharmacy_lane_and_receipt_unlocks(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    _seed_active_mrn(db, ctx)

    unpaid_prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=type(
            "Payload",
            (),
            {
                "drug_name": "Paracetamol",
                "dosage": "1 tab",
                "frequency": "bd",
                "duration": "5 days",
                "instructions": None,
            },
        )(),
    )
    paid_prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=type(
            "Payload",
            (),
            {
                "drug_name": "Paracetamol",
                "dosage": "2 tabs",
                "frequency": "tds",
                "duration": "3 days",
                "instructions": None,
            },
        )(),
    )

    lab_item = BillingItem(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        patient_id=ctx["patient"].id,
        visit_id=ctx["visit"].id,
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        charge_catalog_id=None,
        charge_code="LAB_MANUAL",
        item_name="Urinalysis",
        service_type="LAB_TEST",
        quantity=1,
        unit_price_minor=5000,
        total_minor=5000,
        amount_paid_minor=0,
        currency="NGN",
        status=BillingItemStatus.PENDING,
        created_by=ctx["doctor"].id,
        payment_reference=None,
        paid_at=None,
    )
    db.add(lab_item)
    db.commit()

    CashierPayPointAccessService(db).sync_user_pay_points(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
        role=UserRole.CASHIER,
        allowed_pay_point_ids=[ctx["pharmacy_pay_point"].id],
        default_pay_point_id=ctx["pharmacy_pay_point"].id,
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    db.commit()

    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[paid_prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )

    dashboard = CashierDashboardService(db).get_dashboard(
        clinic_id=ctx["clinic"].id,
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
    )

    assert dashboard["overview"]["pending_charges_count"] == 2
    assert dashboard["overview"]["pharmacy_charges_pending"] == 1
    assert dashboard["overview"]["laboratory_charges_pending"] == 1

    pharmacy_row = dashboard["pharmacy_charges"][0]
    assert pharmacy_row["billing_item_id"] == unpaid_prescription.billing_item_id
    assert pharmacy_row["patient_mrn"] == "KH-0000001-1"
    assert pharmacy_row["assigned_dispensing_unit_name"] == "Adult Pharmacy"
    assert pharmacy_row["destination_hint"] == "Awaiting Payment Clearance — Adult Pharmacy"

    assert dashboard["laboratory_charges"][0]["item_name"] == "Urinalysis"
    assert any(
        "Ready for Pharmacy Dispense — Adult Pharmacy" in row["destination_hints"]
        for row in dashboard["receipts"]
    )
    assert any(
        row["action_type"] == "PHARMACY_UNLOCKED"
        for row in dashboard["activity_audit"]
    )


def test_cashier_pay_point_context_falls_back_to_active_clinic_pay_points(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)

    service = CashierPayPointAccessService(db)

    pay_points = service.list_user_pay_points(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["cashier"].id,
    )
    default_id, allowed_ids, allowed_points = service.context_for_user(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
    )
    resolved = service.resolve_selected_pay_point(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
        selected_pay_point_id=None,
    )

    assert pay_points
    assert {row.id for row in pay_points} == set(allowed_ids)
    assert {row.id for row in pay_points} == {row["id"] for row in allowed_points}
    assert default_id == pay_points[0].id
    assert resolved.id == pay_points[0].id
