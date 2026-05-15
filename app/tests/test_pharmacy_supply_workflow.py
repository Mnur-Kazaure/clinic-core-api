from __future__ import annotations

from datetime import date
from types import SimpleNamespace
import uuid
import pytest
from fastapi import HTTPException

from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.service_line import ServiceLine
from app.models.user import User
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.shared.enums import (
    PharmacyIssueVoucherStatus,
    PharmacyReturnRequestStatus,
    PharmacyRefillRequestStatus,
    UserRole,
)
from app.tests.test_pharmacy_enterprise_workflow import _seed_core_context


def _add_hod_user(db, clinic_id):
    hod = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="pharmacy.hod@test.example",
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
        email="cmd@test.example",
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
        email="pharmacy.store.return@test.example",
        password_hash="x",
        full_name="Pharmacy Store Officer",
        role=UserRole.PHARMACY_STORE_OFFICER.value,
        is_active=True,
    )
    db.add(store_officer)
    db.commit()
    return store_officer


def _seed_store_lot(db, ctx, quantity=40):
    store_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == ctx["clinic"].id,
            ServiceLine.name == "Store",
        )
        .first()
    )
    assert store_unit is not None
    store_lot = PharmacyUnitStockLot(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        service_line_id=store_unit.id,
        inventory_item_id=ctx["inventory_item"].id,
        batch_number="STORE-BATCH-001",
        expiry_date=date(2029, 1, 1),
        quantity_on_hand=quantity,
    )
    db.add(store_lot)
    db.commit()
    return store_unit, store_lot


def _create_acknowledged_voucher(db, ctx, *, approved_quantity=8, issued_quantity=8):
    cmd_user = _add_cmd_user(db, ctx["clinic"].id)
    store_unit, store_lot = _seed_store_lot(db, ctx, quantity=40)

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    db.commit()

    service = PharmacySupplyService(db)
    refill_request = service.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            urgency="HIGH",
            note="Need refill",
            items=[
                SimpleNamespace(
                    inventory_item_id=ctx["inventory_item"].id,
                    requested_quantity=approved_quantity,
                    note=None,
                )
            ],
        ),
    )
    service.review_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=cmd_user,
        request_id=refill_request["id"],
        payload=SimpleNamespace(
            decision="APPROVE",
            review_note=None,
            items=[
                SimpleNamespace(
                    refill_request_item_id=refill_request["items"][0]["id"],
                    approved_quantity=approved_quantity,
                )
            ],
        ),
    )
    voucher = service.issue_stock(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            refill_request_id=refill_request["id"],
            store_unit_id=store_unit.id,
            note="Issue for return flow",
            items=[
                SimpleNamespace(
                    refill_request_item_id=refill_request["items"][0]["id"],
                    batch_number=store_lot.batch_number,
                    expiry_date=store_lot.expiry_date,
                    issued_quantity=issued_quantity,
                )
            ],
        ),
    )
    dispatched = service.dispatch_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        voucher_id=voucher["id"],
        payload=SimpleNamespace(note="Released to unit"),
    )
    acknowledged = service.acknowledge_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        voucher_id=dispatched["id"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            note="Received into unit",
            items=[
                SimpleNamespace(
                    voucher_item_id=dispatched["items"][0]["id"],
                    received_quantity=issued_quantity,
                )
            ],
        ),
    )
    return service, store_unit, store_lot, acknowledged


def test_partial_issue_keeps_refill_request_partially_received(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    cmd_user = _add_cmd_user(db, ctx["clinic"].id)
    store_unit, store_lot = _seed_store_lot(db, ctx, quantity=40)

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    db.commit()

    service = PharmacySupplyService(db)
    refill_request = service.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            urgency="HIGH",
            note="Need refill",
            items=[
                SimpleNamespace(
                    inventory_item_id=ctx["inventory_item"].id,
                    requested_quantity=10,
                    note=None,
                )
            ],
        ),
    )

    reviewed = service.review_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=cmd_user,
        request_id=refill_request["id"],
        payload=SimpleNamespace(
            decision="APPROVE",
            review_note="Partial approved",
            items=[
                SimpleNamespace(
                    refill_request_item_id=refill_request["items"][0]["id"],
                    approved_quantity=8,
                )
            ],
        ),
    )
    assert reviewed["status"] == PharmacyRefillRequestStatus.APPROVED

    voucher = service.issue_stock(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            refill_request_id=refill_request["id"],
            store_unit_id=store_unit.id,
            note="Partial issue",
            items=[
                SimpleNamespace(
                    refill_request_item_id=refill_request["items"][0]["id"],
                    batch_number=store_lot.batch_number,
                    expiry_date=store_lot.expiry_date,
                    issued_quantity=5,
                )
            ],
        ),
    )

    assert voucher["status"] == PharmacyIssueVoucherStatus.PREPARED
    voucher = service.dispatch_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        voucher_id=voucher["id"],
        payload=SimpleNamespace(note="Released to unit"),
    )
    assert voucher["status"] == PharmacyIssueVoucherStatus.DISPATCHED
    db.refresh(store_lot)
    db.refresh(ctx["inventory_item"])
    assert store_lot.quantity_on_hand == 35
    assert ctx["inventory_item"].stock_quantity == 45

    acknowledged = service.acknowledge_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        voucher_id=voucher["id"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            note="Received partial",
            items=[
                SimpleNamespace(
                    voucher_item_id=voucher["items"][0]["id"],
                    received_quantity=5,
                )
            ],
        ),
    )

    assert acknowledged["status"] == PharmacyIssueVoucherStatus.ACKNOWLEDGED
    request_state = service.get_refill_request(
        clinic_id=ctx["clinic"].id,
        request_id=refill_request["id"],
    )
    assert request_state["status"] == PharmacyRefillRequestStatus.ACKNOWLEDGED


def test_full_issue_and_acknowledgement_marks_request_received(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    cmd_user = _add_cmd_user(db, ctx["clinic"].id)
    store_unit, store_lot = _seed_store_lot(db, ctx, quantity=20)

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    db.commit()

    service = PharmacySupplyService(db)
    refill_request = service.create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            urgency=None,
            note=None,
            items=[
                SimpleNamespace(
                    inventory_item_id=ctx["inventory_item"].id,
                    requested_quantity=6,
                    note=None,
                )
            ],
        ),
    )
    service.review_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=cmd_user,
        request_id=refill_request["id"],
        payload=SimpleNamespace(decision="APPROVE", review_note=None, items=None),
    )

    voucher = service.issue_stock(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            refill_request_id=refill_request["id"],
            store_unit_id=store_unit.id,
            note="Full issue",
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
    assert voucher["status"] == PharmacyIssueVoucherStatus.PREPARED
    voucher = service.dispatch_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        voucher_id=voucher["id"],
        payload=SimpleNamespace(note="Released to unit"),
    )

    acknowledged = service.acknowledge_issue_voucher(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        voucher_id=voucher["id"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            note=None,
            items=[
                SimpleNamespace(
                    voucher_item_id=voucher["items"][0]["id"],
                    received_quantity=6,
                )
            ],
        ),
    )

    assert acknowledged["status"] == PharmacyIssueVoucherStatus.ACKNOWLEDGED
    request_state = service.get_refill_request(
        clinic_id=ctx["clinic"].id,
        request_id=refill_request["id"],
    )
    assert request_state["status"] == PharmacyRefillRequestStatus.CLOSED

    received_lot = (
        db.query(PharmacyUnitStockLot)
        .filter(
            PharmacyUnitStockLot.clinic_id == ctx["clinic"].id,
            PharmacyUnitStockLot.service_line_id == ctx["adult_unit"].id,
            PharmacyUnitStockLot.inventory_item_id == ctx["inventory_item"].id,
            PharmacyUnitStockLot.batch_number == store_lot.batch_number,
        )
        .first()
    )
    assert received_lot is not None
    assert received_lot.quantity_on_hand == 6


def test_return_to_store_accept_and_receive_updates_stock_with_reference(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    store_officer = _add_store_officer_user(db, ctx["clinic"].id)
    service, store_unit, store_lot, voucher = _create_acknowledged_voucher(
        db,
        ctx,
        approved_quantity=8,
        issued_quantity=8,
    )

    return_request = service.create_return_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            issue_voucher_id=voucher["id"],
            issue_voucher_item_id=voucher["items"][0]["id"],
            quantity_now_returned=3,
            reason_code="EXCESS_UNUSED",
            reason_note="Unused ward balance",
        ),
    )
    assert return_request["status"] == PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW

    reviewed = service.review_return_request(
        clinic_id=ctx["clinic"].id,
        actor=store_officer,
        return_request_id=return_request["id"],
        payload=SimpleNamespace(
            decision="ACCEPT",
            review_note="Return accepted into store",
        ),
    )
    assert reviewed["status"] == PharmacyReturnRequestStatus.RETURN_ACCEPTED

    received = service.receive_return_request(
        clinic_id=ctx["clinic"].id,
        actor=store_officer,
        return_request_id=return_request["id"],
        payload=SimpleNamespace(receive_note="Stock received back into store"),
    )
    assert received["status"] == PharmacyReturnRequestStatus.RETURN_RECEIVED
    assert received["quantity_received"] == 3

    db.refresh(store_lot)
    db.refresh(ctx["inventory_item"])
    assert store_lot.quantity_on_hand == 35
    assert ctx["inventory_item"].stock_quantity == 45

    unit_lot = (
        db.query(PharmacyUnitStockLot)
        .filter(
            PharmacyUnitStockLot.clinic_id == ctx["clinic"].id,
            PharmacyUnitStockLot.service_line_id == ctx["adult_unit"].id,
            PharmacyUnitStockLot.inventory_item_id == ctx["inventory_item"].id,
            PharmacyUnitStockLot.batch_number == store_lot.batch_number,
        )
        .first()
    )
    assert unit_lot is not None
    assert unit_lot.quantity_on_hand == 5


def test_return_to_store_blocks_over_return_against_open_requests(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    service, _, _, voucher = _create_acknowledged_voucher(
        db,
        ctx,
        approved_quantity=6,
        issued_quantity=6,
    )

    first_return = service.create_return_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            issue_voucher_id=voucher["id"],
            issue_voucher_item_id=voucher["items"][0]["id"],
            quantity_now_returned=4,
            reason_code="EXCESS_UNUSED",
            reason_note=None,
        ),
    )
    assert first_return["quantity_now_returned"] == 4

    with pytest.raises(HTTPException) as exc_info:
        service.create_return_request(
            clinic_id=ctx["clinic"].id,
            actor=ctx["pharmacist"],
            payload=SimpleNamespace(
                unit_id=ctx["adult_unit"].id,
                issue_voucher_id=voucher["id"],
                issue_voucher_item_id=voucher["items"][0]["id"],
                quantity_now_returned=3,
                reason_code="EXCESS_UNUSED",
                reason_note="Would exceed eligible balance",
            ),
        )

    assert "eligible issued balance" in str(exc_info.value)


def test_return_to_store_rejection_preserves_stock(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    store_officer = _add_store_officer_user(db, ctx["clinic"].id)
    service, store_unit, store_lot, voucher = _create_acknowledged_voucher(
        db,
        ctx,
        approved_quantity=5,
        issued_quantity=5,
    )

    return_request = service.create_return_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=SimpleNamespace(
            unit_id=ctx["adult_unit"].id,
            issue_voucher_id=voucher["id"],
            issue_voucher_item_id=voucher["items"][0]["id"],
            quantity_now_returned=2,
            reason_code="WRONG_ISSUE",
            reason_note="Opened pack cannot return",
        ),
    )

    rejected = service.review_return_request(
        clinic_id=ctx["clinic"].id,
        actor=store_officer,
        return_request_id=return_request["id"],
        payload=SimpleNamespace(
            decision="REJECT",
            review_note="Rejected by store on inspection policy",
        ),
    )
    assert rejected["status"] == PharmacyReturnRequestStatus.RETURN_REJECTED

    db.refresh(store_lot)
    db.refresh(ctx["inventory_item"])
    assert store_lot.quantity_on_hand == 35
    assert ctx["inventory_item"].stock_quantity == 45
