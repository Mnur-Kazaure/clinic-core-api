from __future__ import annotations

from datetime import date
from types import SimpleNamespace
import uuid

from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.service_line import ServiceLine
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.pharmacy_dispensing_dashboard_service import (
    PharmacyDispensingDashboardService,
)
from app.services.pharmacy_service import PharmacyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.services.prescription_service import PrescriptionService
from app.shared.enums import BillingReasonCode, UserRole
from app.tests.test_pharmacy_enterprise_workflow import (
    _seed_core_context,
    _seed_governed_catalog_inventory,
)


def _seed_secondary_inventory(db, clinic_id, pharmacist_id):
    item = _seed_governed_catalog_inventory(
        db,
        clinic_id=clinic_id,
        actor_id=pharmacist_id,
        generic_name="Amoxicillin",
        dosage_form="Capsule",
        strength="500mg",
        dispense_unit="Capsule",
        selling_price_minor=25000,
        stock_quantity=25,
        low_stock_threshold=5,
    )
    db.commit()
    return item["inventory_item"]


def test_dispensing_dashboard_summarizes_queue_stock_and_reassignment(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    amoxicillin = _seed_secondary_inventory(
        db,
        ctx["clinic"].id,
        ctx["pharmacist"].id,
    )

    adult_unit = ctx["adult_unit"]
    pediatric_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == ctx["clinic"].id,
            ServiceLine.name == "Pediatric Pharmacy",
        )
        .first()
    )
    assert pediatric_unit is not None

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[adult_unit.id, pediatric_unit.id],
        default_unit_id=adult_unit.id,
    )
    db.commit()

    stocked_lot = PharmacyUnitStockLot(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        service_line_id=adult_unit.id,
        inventory_item_id=ctx["inventory_item"].id,
        batch_number="ADULT-BATCH-001",
        expiry_date=date(2028, 1, 1),
        quantity_on_hand=12,
    )
    db.add(stocked_lot)
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
    awaiting_payment = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
          drug_name="Amoxicillin",
          dosage="1 cap",
          frequency="tds",
          duration="7 days",
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

    PharmacyService(db).reassign_prescription(
        prescription=ready_prescription,
        actor=ctx["pharmacist"],
        target_unit_id=pediatric_unit.id,
        reason="OVERLOAD",
        note="Move out temporarily",
    )
    PharmacyService(db).reassign_prescription(
        prescription=ready_prescription,
        actor=ctx["pharmacist"],
        target_unit_id=adult_unit.id,
        reason="SPECIALIZED_UNIT",
        note="Return to adult bench",
    )

    dashboard = PharmacyDispensingDashboardService(db).get_dashboard(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        selected_unit_id=adult_unit.id,
    )

    assert dashboard.unit_id == adult_unit.id
    assert dashboard.overview.ready_to_dispense == 1
    assert dashboard.overview.awaiting_payment_clearance == 1
    assert dashboard.overview.reassigned == 1
    assert dashboard.overview.out_of_stock == 1
    assert any(row.item_name == "Amoxicillin" for row in dashboard.alerts)
    ready_row = next(
        row for row in dashboard.prescriptions if row.prescription_id == ready_prescription.id
    )
    assert ready_row.recently_reassigned is True
    assert ready_row.local_stock_status == "IN_STOCK"
    blocked_row = next(
        row for row in dashboard.prescriptions if row.prescription_id == awaiting_payment.id
    )
    assert blocked_row.local_stock_status == "OUT_OF_STOCK"

    detail = PharmacyDispensingDashboardService(db).get_prescription_detail_context(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        selected_unit_id=adult_unit.id,
        prescription=ready_prescription,
    )
    assert detail["local_stock_available_quantity"] == 12
    assert detail["local_stock_status"] == "IN_STOCK"
    assert detail["available_stock_lots"][0]["batch_number"] == stocked_lot.batch_number


def test_dispensing_dashboard_keeps_partial_dispense_in_ready_lane(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    lot = PharmacyUnitStockLot(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        service_line_id=ctx["adult_unit"].id,
        inventory_item_id=ctx["inventory_item"].id,
        batch_number="PARTIAL-DASH-001",
        expiry_date=date(2028, 1, 1),
        quantity_on_hand=12,
    )
    db.add(lot)

    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=10,
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
        billing_item_ids=[prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )

    PharmacyService(db).dispense_prescription(
        prescription,
        SimpleNamespace(
            pharmacist_id=ctx["pharmacist"].id,
            quantity=6,
            unit_id=ctx["adult_unit"].id,
            stock_lot_id=lot.id,
        ),
    )

    dashboard = PharmacyDispensingDashboardService(db).get_dashboard(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        selected_unit_id=ctx["adult_unit"].id,
    )

    assert dashboard.overview.ready_to_dispense == 1
    row = next(
        item for item in dashboard.prescriptions if item.prescription_id == prescription.id
    )
    assert (
        row.readiness_state.value == "PARTIALLY_DISPENSED"
    )
    assert row.quantity_prescribed == 10
    assert row.quantity_dispensed_total == 6
    assert row.quantity_remaining == 4
    assert any(
        audit.action_type == "PARTIAL_DISPENSED"
        for audit in dashboard.activity_audit
    )
