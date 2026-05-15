from __future__ import annotations

from datetime import date
from types import SimpleNamespace
import uuid

from app.models.event_log import EventLog
from app.models.service_line import ServiceLine
from app.models.user import User
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.pharmacy_hod_dashboard_service import PharmacyHodDashboardService
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.services.prescription_service import PrescriptionService
from app.shared.enums import BillingReasonCode, PharmacyPrescriptionWorkflowStatus, UserRole
from app.tests.test_pharmacy_enterprise_workflow import _seed_core_context


def _add_hod_user(db, clinic_id):
    hod = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="pharmacy.hod.dashboard@test.example",
        password_hash="x",
        full_name="Pharmacy HOD",
        role=UserRole.PHARMACY_HOD.value,
        is_active=True,
    )
    db.add(hod)
    db.commit()
    return hod


def _add_cmd_user(db, clinic_id):
    cmd_user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="cmd.dashboard@test.example",
        password_hash="x",
        full_name="Chief Medical Director",
        role=UserRole.CMD.value,
        is_active=True,
    )
    db.add(cmd_user)
    db.commit()
    return cmd_user


def test_pharmacy_hod_dashboard_aggregates_overview_and_finance(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    hod = _add_hod_user(db, ctx["clinic"].id)
    _add_cmd_user(db, ctx["clinic"].id)

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    db.commit()

    ready_prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            instructions=None,
        ),
    )
    awaiting_prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="tds",
            duration="3 days",
            instructions=None,
        ),
    )

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
        billing_item_ids=[ready_prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )

    refill_request = PharmacySupplyService(db).create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            urgency="HIGH",
            note="Need replenishment",
            items=[
                SimpleNamespace(
                    inventory_item_id=ctx["inventory_item"].id,
                    requested_quantity=5,
                    note=None,
                )
            ],
        ),
    )
    assert refill_request["status"].value == "AWAITING_CMD_APPROVAL"

    dashboard = PharmacyHodDashboardService(db).get_dashboard(
        clinic_id=ctx["clinic"].id,
        start_date=date.today(),
        end_date=date.today(),
    )

    assert dashboard.overview.ready_to_dispense == 1
    assert dashboard.overview.awaiting_payment_clearance == 1
    assert dashboard.overview.pending_refill_requests == 1
    assert dashboard.sales_revenue.receipt_count == 1
    assert any(unit.unit_name == "Adult Pharmacy" for unit in dashboard.unit_summary)
    assert any(point.pay_point_name == ctx["pharmacy_pay_point"].name for point in dashboard.pay_point_performance)
    assert any(row.receipt_number for row in dashboard.receipt_register)
    assert any(row.request_id == refill_request["id"] for row in dashboard.pending_approvals)

    adult_unit = next(unit for unit in dashboard.unit_summary if unit.unit_name == "Adult Pharmacy")
    assert adult_unit.ready_to_dispense == 1
    assert adult_unit.awaiting_payment_clearance == 1

    pay_point = next(
        row for row in dashboard.pay_point_performance if row.pay_point_name == ctx["pharmacy_pay_point"].name
    )
    assert pay_point.transaction_count == 1
    assert pay_point.awaiting_clearance_count == 1


def test_pharmacy_hod_updates_staff_unit_assignment_and_audits(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    hod = _add_hod_user(db, ctx["clinic"].id)
    nhis_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == ctx["clinic"].id,
            ServiceLine.name == "NHIS Pharmacy",
        )
        .first()
    )
    assert nhis_unit is not None

    updated = PharmacyHodDashboardService(db).update_staff_assignment(
        clinic_id=ctx["clinic"].id,
        actor=hod,
        staff_id=ctx["pharmacist"].id,
        payload=SimpleNamespace(
            allowed_unit_ids=[ctx["adult_unit"].id, nhis_unit.id],
            default_unit_id=nhis_unit.id,
        ),
    )

    assert updated.default_unit_id == nhis_unit.id
    assert {unit.name for unit in updated.assigned_units} == {"Adult Pharmacy", "NHIS Pharmacy"}

    audit_event = (
        db.query(EventLog)
        .filter(
            EventLog.clinic_id == ctx["clinic"].id,
            EventLog.event_type == "PHARMACY_STAFF_ASSIGNMENT_UPDATED",
        )
        .first()
    )
    assert audit_event is not None
