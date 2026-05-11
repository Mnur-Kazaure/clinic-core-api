from __future__ import annotations

from datetime import date
from types import SimpleNamespace
import uuid

from app.models.event_log import EventLog
from app.models.pharmacy_stock_movement import PharmacyStockMovement
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.service_line import ServiceLine
from app.models.user import User
from app.services.pharmacy_store_dashboard_service import PharmacyStoreDashboardService
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.shared.enums import (
    PharmacyRefillRequestStatus,
    PharmacyReturnRequestStatus,
    PharmacyUnitCategory,
    UserRole,
)
from app.tests.test_pharmacy_enterprise_workflow import _seed_core_context


def _add_hod_user(db, clinic_id):
    hod = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="pharmacy.hod.store@test.example",
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
        email="cmd.store@test.example",
        password_hash="x",
        full_name="Chief Medical Director",
        role=UserRole.CMD.value,
        is_active=True,
    )
    db.add(cmd_user)
    db.commit()
    return cmd_user


def _add_store_officer_user(db, clinic_id):
    store_officer = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="pharmacy.store.officer@test.example",
        password_hash="x",
        full_name="Pharmacy Store Officer",
        role=UserRole.PHARMACY_STORE_OFFICER.value,
        is_active=True,
    )
    db.add(store_officer)
    db.commit()
    return store_officer


def _get_store_unit(db, clinic_id):
    return (
        db.query(ServiceLine)
        .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
        .filter(
            ServiceLine.clinic_id == clinic_id,
            PharmacyUnitProfile.unit_category == PharmacyUnitCategory.STORE,
        )
        .first()
    )


def _get_unit_by_name(db, clinic_id, name: str):
    return (
        db.query(ServiceLine)
        .filter(ServiceLine.clinic_id == clinic_id, ServiceLine.name == name)
        .first()
    )


def test_store_dashboard_surfaces_reservations_and_backorders(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    cmd_user = _add_cmd_user(db, ctx["clinic"].id)
    _add_store_officer_user(db, ctx["clinic"].id)
    nhis_unit = _get_unit_by_name(db, ctx["clinic"].id, "NHIS Pharmacy")
    assert nhis_unit is not None

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id, nhis_unit.id],
        default_unit_id=ctx["adult_unit"].id,
    )
    db.commit()

    supply = PharmacySupplyService(db)
    adult_request = supply.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            urgency="EMERGENCY",
            note="Adult stockout",
            items=[SimpleNamespace(inventory_item_id=ctx["inventory_item"].id, requested_quantity=40, note=None)],
        ),
    )
    nhis_request = supply.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=nhis_unit.id,
            urgency="ROUTINE",
            note="NHIS request",
            items=[SimpleNamespace(inventory_item_id=ctx["inventory_item"].id, requested_quantity=20, note=None)],
        ),
    )

    supply.review_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=cmd_user,
        request_id=adult_request["id"],
        payload=SimpleNamespace(
            decision="APPROVE",
            review_note=None,
            items=[SimpleNamespace(refill_request_item_id=adult_request["items"][0]["id"], approved_quantity=40)],
        ),
    )
    reviewed_nhis = supply.review_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=cmd_user,
        request_id=nhis_request["id"],
        payload=SimpleNamespace(
            decision="APPROVE",
            review_note=None,
            items=[SimpleNamespace(refill_request_item_id=nhis_request["items"][0]["id"], approved_quantity=20)],
        ),
    )

    assert reviewed_nhis["status"] == PharmacyRefillRequestStatus.BACKORDER_PENDING

    store_unit = _get_store_unit(db, ctx["clinic"].id)
    assert store_unit is not None

    dashboard = PharmacyStoreDashboardService(db).get_dashboard(
        clinic_id=ctx["clinic"].id,
        start_date=date.today(),
        end_date=date.today(),
        store_unit_id=store_unit.id,
    )

    inventory_row = next(row for row in dashboard.inventory if row.inventory_item_id == ctx["inventory_item"].id)
    assert inventory_row.reserved_quantity == 50
    assert inventory_row.available_quantity == 0

    nhis_row = next(row for row in dashboard.approved_requests if row.request_id == nhis_request["id"])
    assert nhis_row.status == PharmacyRefillRequestStatus.BACKORDER_PENDING
    assert nhis_row.backorder_pending is True
    assert nhis_row.total_reserved_quantity == 10
    assert nhis_row.items[0].backorder_quantity == 10


def test_store_receive_stock_rebalances_backorders_and_records_event(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    cmd_user = _add_cmd_user(db, ctx["clinic"].id)
    store_officer = _add_store_officer_user(db, ctx["clinic"].id)
    nhis_unit = _get_unit_by_name(db, ctx["clinic"].id, "NHIS Pharmacy")
    store_unit = _get_store_unit(db, ctx["clinic"].id)
    assert nhis_unit is not None
    assert store_unit is not None

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id, nhis_unit.id],
        default_unit_id=ctx["adult_unit"].id,
    )
    db.commit()

    supply = PharmacySupplyService(db)
    adult_request = supply.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            urgency="URGENT",
            note=None,
            items=[SimpleNamespace(inventory_item_id=ctx["inventory_item"].id, requested_quantity=45, note=None)],
        ),
    )
    nhis_request = supply.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=nhis_unit.id,
            urgency="ROUTINE",
            note=None,
            items=[SimpleNamespace(inventory_item_id=ctx["inventory_item"].id, requested_quantity=20, note=None)],
        ),
    )

    for refill_request in (adult_request, nhis_request):
        supply.review_refill_request(
            clinic_id=ctx["clinic"].id,
            actor=cmd_user,
            request_id=refill_request["id"],
            payload=SimpleNamespace(decision="APPROVE", review_note=None, items=None),
        )

    service = PharmacyStoreDashboardService(db)
    received = service.receive_stock(
        clinic_id=ctx["clinic"].id,
        actor=store_officer,
        payload=SimpleNamespace(
            store_unit_id=store_unit.id,
            inventory_item_id=ctx["inventory_item"].id,
            batch_number="STORE-REC-001",
            expiry_date=date(2029, 1, 1),
            quantity_received=15,
            unit_cost_minor=None,
            source_reference_note="Emergency supplier delivery",
        ),
    )

    assert received.stock_quantity == 65

    nhis_state = supply.get_refill_request(
        clinic_id=ctx["clinic"].id,
        request_id=nhis_request["id"],
    )
    assert nhis_state["status"] == PharmacyRefillRequestStatus.APPROVED
    assert nhis_state["items"][0]["reserved_quantity"] == 20

    event = (
        db.query(EventLog)
        .filter(
            EventLog.clinic_id == ctx["clinic"].id,
            EventLog.event_type == "PHARMACY_STORE_STOCK_RECEIVED",
        )
        .first()
    )
    assert event is not None

    lot = (
        db.query(PharmacyUnitStockLot)
        .filter(
            PharmacyUnitStockLot.clinic_id == ctx["clinic"].id,
            PharmacyUnitStockLot.service_line_id == store_unit.id,
            PharmacyUnitStockLot.inventory_item_id == ctx["inventory_item"].id,
            PharmacyUnitStockLot.batch_number == "STORE-REC-001",
        )
        .first()
    )
    assert lot is not None
    assert lot.quantity_on_hand == 15


def test_store_adjustment_is_audited_and_visible_in_dashboard(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    store_officer = _add_store_officer_user(db, ctx["clinic"].id)
    store_unit = _get_store_unit(db, ctx["clinic"].id)
    assert store_unit is not None

    lot = PharmacyUnitStockLot(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        service_line_id=store_unit.id,
        inventory_item_id=ctx["inventory_item"].id,
        batch_number="ADJ-BATCH-001",
        expiry_date=date(2028, 6, 1),
        quantity_on_hand=12,
    )
    db.add(lot)
    db.commit()

    service = PharmacyStoreDashboardService(db)
    adjusted = service.adjust_stock(
        clinic_id=ctx["clinic"].id,
        actor=store_officer,
        payload=SimpleNamespace(
            store_unit_id=store_unit.id,
            inventory_item_id=ctx["inventory_item"].id,
            batch_number=lot.batch_number,
            expiry_date=lot.expiry_date,
            quantity_delta=-4,
            reason="Cycle count correction",
        ),
    )

    assert adjusted.stock_quantity == 46

    movement = (
        db.query(PharmacyStockMovement)
        .filter(
            PharmacyStockMovement.clinic_id == ctx["clinic"].id,
            PharmacyStockMovement.reference_type == "STOCK_ADJUSTMENT",
        )
        .first()
    )
    assert movement is not None

    event = (
        db.query(EventLog)
        .filter(
            EventLog.clinic_id == ctx["clinic"].id,
            EventLog.event_type == "PHARMACY_STORE_ADJUSTMENT_RECORDED",
        )
        .first()
    )
    assert event is not None

    dashboard = service.get_dashboard(
        clinic_id=ctx["clinic"].id,
        start_date=date.today(),
        end_date=date.today(),
        store_unit_id=store_unit.id,
    )
    assert any(row.reference_number for row in dashboard.adjustments_reconciliation)
    assert any(row.action_type == "PHARMACY_STORE_ADJUSTMENT_RECORDED" for row in dashboard.activity_audit)


def test_store_dashboard_surfaces_return_requests_and_pending_reviews(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    cmd_user = _add_cmd_user(db, ctx["clinic"].id)
    store_officer = _add_store_officer_user(db, ctx["clinic"].id)
    store_unit = _get_store_unit(db, ctx["clinic"].id)
    assert store_unit is not None

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    db.commit()

    store_lot = PharmacyUnitStockLot(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        service_line_id=store_unit.id,
        inventory_item_id=ctx["inventory_item"].id,
        batch_number="RETURN-BATCH-001",
        expiry_date=date(2029, 1, 1),
        quantity_on_hand=20,
    )
    db.add(store_lot)
    db.commit()

    supply = PharmacySupplyService(db)
    refill_request = supply.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            urgency="ROUTINE",
            note="Return workflow stock",
            items=[SimpleNamespace(inventory_item_id=ctx["inventory_item"].id, requested_quantity=6, note=None)],
        ),
    )
    supply.review_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=cmd_user,
        request_id=refill_request["id"],
        payload=SimpleNamespace(decision="APPROVE", review_note=None, items=None),
    )
    voucher = supply.issue_stock(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            refill_request_id=refill_request["id"],
            store_unit_id=store_unit.id,
            note="Voucher for return test",
            items=[
                SimpleNamespace(
                    refill_request_item_id=refill_request["items"][0]["id"],
                    batch_number=store_lot.batch_number,
                    expiry_date=store_lot.expiry_date,
                    issued_quantity=6,
                )
            ],
        ),
    )
    dispatched = supply.dispatch_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=store_officer,
        voucher_id=voucher["id"],
        payload=SimpleNamespace(note="Issued to unit"),
    )
    supply.acknowledge_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        voucher_id=dispatched["id"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            note="Received into unit",
            items=[
                SimpleNamespace(
                    voucher_item_id=dispatched["items"][0]["id"],
                    received_quantity=6,
                )
            ],
        ),
    )

    return_request = supply.create_return_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            issue_voucher_id=dispatched["id"],
            issue_voucher_item_id=dispatched["items"][0]["id"],
            quantity_now_returned=2,
            reason_code="EXCESS_UNUSED",
            reason_note="Unused supply balance",
        ),
    )
    assert return_request["status"] == PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW

    dashboard = PharmacyStoreDashboardService(db).get_dashboard(
        clinic_id=ctx["clinic"].id,
        start_date=date.today(),
        end_date=date.today(),
        store_unit_id=store_unit.id,
    )

    assert dashboard.overview.pending_return_reviews == 1
    assert any(row.return_number == return_request["return_number"] for row in dashboard.return_requests)
    assert any(row.movement_type == "ISSUE" for row in dashboard.movement_history)
