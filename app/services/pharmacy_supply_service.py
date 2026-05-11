from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_issue_voucher import PharmacyIssueVoucher
from app.models.pharmacy_issue_voucher_item import PharmacyIssueVoucherItem
from app.models.pharmacy_return_request import PharmacyReturnRequest
from app.models.pharmacy_refill_request import PharmacyRefillRequest
from app.models.pharmacy_refill_request_item import PharmacyRefillRequestItem
from app.models.pharmacy_stock_movement import PharmacyStockMovement
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.service_line import ServiceLine
from app.models.user import User
from app.services.event_service import EventService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.shared.enums import (
    PharmacyIssueVoucherStatus,
    PharmacyReturnReasonCode,
    PharmacyReturnRequestStatus,
    PharmacyRequestType,
    PharmacyRefillRequestStatus,
    PharmacyUnitCategory,
    UserRole,
)


class PharmacySupplyService:
    REQUESTS_WITH_ACTIVE_RESERVATIONS = {
        PharmacyRefillRequestStatus.APPROVED,
        PharmacyRefillRequestStatus.BACKORDERED,
        PharmacyRefillRequestStatus.BACKORDER_PENDING,
        PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS,
        PharmacyRefillRequestStatus.PARTIALLY_ISSUED,
        PharmacyRefillRequestStatus.DISPATCHED,
        PharmacyRefillRequestStatus.PARTIALLY_RECEIVED,
        PharmacyRefillRequestStatus.ACKNOWLEDGED,
    }

    def __init__(self, db: Session):
        self.db = db

    def rebalance_reservations(self, *, clinic_id: UUID) -> None:
        self._rebalance_reservations(clinic_id=clinic_id)

    def create_refill_request(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        payload,
    ) -> dict:
        requesting_unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=getattr(payload, "unit_id", None),
        )
        request = PharmacyRefillRequest(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            requesting_unit_id=requesting_unit.id,
            requested_by=actor.id,
            request_type=getattr(payload, "request_type", PharmacyRequestType.PHARMACY_REFILL),
            urgency=(payload.urgency or None),
            note=(payload.note or None),
            status=PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL,
        )
        self.db.add(request)
        self.db.flush()

        inventory_ids = [item.inventory_item_id for item in payload.items]
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == clinic_id,
                PharmacyInventoryItem.id.in_(inventory_ids),
            )
            .all()
        )
        inventory_map = {item.id: item for item in inventory_items}
        if len(inventory_map) != len(set(inventory_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more refill items reference unknown inventory",
            )

        for item in payload.items:
            self.db.add(
                PharmacyRefillRequestItem(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    refill_request_id=request.id,
                    inventory_item_id=item.inventory_item_id,
                    requested_quantity=item.requested_quantity,
                    note=item.note,
                )
            )

        EventService(self.db).build_event(
            event_type="PHARMACY_REFILL_REQUESTED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "refill_request_id": str(request.id),
                "requesting_unit_id": str(requesting_unit.id),
                "request_type": self._enum_value(request.request_type),
                "item_count": len(payload.items),
            },
        )
        self.db.commit()
        return self.get_refill_request(clinic_id=clinic_id, request_id=request.id)

    def list_unit_refill_requests(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        selected_unit_id: UUID | None = None,
    ) -> list[dict]:
        requesting_unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=selected_unit_id,
        )
        rows = (
            self.db.query(PharmacyRefillRequest)
            .filter(
                PharmacyRefillRequest.clinic_id == clinic_id,
                PharmacyRefillRequest.requesting_unit_id == requesting_unit.id,
            )
            .order_by(PharmacyRefillRequest.requested_at.desc())
            .all()
        )
        return self._serialize_refill_requests(rows)

    def list_hod_refill_requests(
        self,
        *,
        clinic_id: UUID,
        status_filter: PharmacyRefillRequestStatus | None = None,
    ) -> list[dict]:
        query = self.db.query(PharmacyRefillRequest).filter(
            PharmacyRefillRequest.clinic_id == clinic_id
        )
        if status_filter is not None:
            query = query.filter(PharmacyRefillRequest.status == status_filter)
        rows = query.order_by(PharmacyRefillRequest.requested_at.desc()).all()
        return self._serialize_refill_requests(rows)

    def list_cmd_refill_requests(
        self,
        *,
        clinic_id: UUID,
        status_filter: PharmacyRefillRequestStatus | None = None,
    ) -> list[dict]:
        query = self.db.query(PharmacyRefillRequest).filter(
            PharmacyRefillRequest.clinic_id == clinic_id
        )
        if status_filter is None:
            query = query.filter(
                PharmacyRefillRequest.status.in_(
                    {
                        PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL,
                        PharmacyRefillRequestStatus.APPROVED,
                        PharmacyRefillRequestStatus.REJECTED,
                    }
                )
            )
        else:
            query = query.filter(PharmacyRefillRequest.status == status_filter)
        rows = query.order_by(PharmacyRefillRequest.requested_at.desc()).all()
        return self._serialize_refill_requests(rows)

    def get_refill_request(self, *, clinic_id: UUID, request_id: UUID) -> dict:
        request = self._get_refill_request(clinic_id=clinic_id, request_id=request_id)
        return self._serialize_refill_requests([request])[0]

    def review_refill_request(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        request_id: UUID,
        payload,
    ) -> dict:
        self._require_cmd_actor(actor)
        request = self._get_refill_request(clinic_id=clinic_id, request_id=request_id)
        if request.status not in {
            PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL,
            PharmacyRefillRequestStatus.PENDING,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only awaiting-CMD-approval requests can be reviewed",
            )

        items = self._get_refill_request_items(request.id)
        decision = payload.decision.upper()
        if decision == "REJECT":
            for item in items:
                item.approved_quantity = 0
                item.reserved_quantity = 0
                self.db.add(item)
            request.status = PharmacyRefillRequestStatus.REJECTED
        else:
            review_overrides = {
                item.refill_request_item_id: item.approved_quantity
                for item in (payload.items or [])
            }
            any_approved = False
            for item in items:
                approved_quantity = review_overrides.get(item.id, item.requested_quantity)
                item.approved_quantity = approved_quantity
                item.reserved_quantity = 0
                any_approved = any_approved or approved_quantity > 0
                self.db.add(item)
            if not any_approved:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Approved refill request must contain at least one approved quantity",
                )
            request.status = PharmacyRefillRequestStatus.APPROVED

        request.reviewed_by = actor.id
        request.reviewed_at = datetime.now(timezone.utc)
        request.review_note = payload.review_note or None
        request.hod_visible_at = request.reviewed_at
        self.db.add(request)
        self.db.flush()
        self._rebalance_reservations(clinic_id=clinic_id)
        request.status = self._recalculate_refill_request_status(request.id)
        self.db.add(request)

        EventService(self.db).build_event(
            event_type=(
                "PHARMACY_CMD_REJECTED"
                if decision == "REJECT"
                else "PHARMACY_CMD_APPROVED"
            ),
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "refill_request_id": str(request.id),
                "decision": decision,
                "status": request.status.value,
                "requesting_unit_id": str(request.requesting_unit_id),
            },
        )
        self.db.commit()
        return self.get_refill_request(clinic_id=clinic_id, request_id=request.id)

    def list_store_issue_vouchers(
        self,
        *,
        clinic_id: UUID,
        store_unit_id: UUID,
    ) -> list[dict]:
        self._get_store_unit(clinic_id=clinic_id, store_unit_id=store_unit_id)
        rows = (
            self.db.query(PharmacyIssueVoucher)
            .filter(
                PharmacyIssueVoucher.clinic_id == clinic_id,
                PharmacyIssueVoucher.store_unit_id == store_unit_id,
            )
            .order_by(PharmacyIssueVoucher.prepared_at.desc().nullslast(), PharmacyIssueVoucher.issued_at.desc().nullslast())
            .all()
        )
        return self._serialize_issue_vouchers(rows)

    def list_unit_issue_vouchers(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        selected_unit_id: UUID | None = None,
    ) -> list[dict]:
        receiving_unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=selected_unit_id,
        )
        rows = (
            self.db.query(PharmacyIssueVoucher)
            .filter(
                PharmacyIssueVoucher.clinic_id == clinic_id,
                PharmacyIssueVoucher.receiving_unit_id == receiving_unit.id,
            )
            .order_by(PharmacyIssueVoucher.prepared_at.desc().nullslast(), PharmacyIssueVoucher.issued_at.desc().nullslast())
            .all()
        )
        return self._serialize_issue_vouchers(rows)

    def get_issue_voucher(self, *, clinic_id: UUID, voucher_id: UUID) -> dict:
        voucher = self._get_issue_voucher(clinic_id=clinic_id, voucher_id=voucher_id)
        return self._serialize_issue_vouchers([voucher])[0]

    def create_issue_voucher(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        payload,
    ) -> dict:
        request = self._get_refill_request(
            clinic_id=clinic_id,
            request_id=payload.refill_request_id,
        )
        if request.status not in {
            PharmacyRefillRequestStatus.APPROVED,
            PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS,
            PharmacyRefillRequestStatus.BACKORDERED,
            PharmacyRefillRequestStatus.BACKORDER_PENDING,
            PharmacyRefillRequestStatus.PARTIALLY_ISSUED,
            PharmacyRefillRequestStatus.DISPATCHED,
            PharmacyRefillRequestStatus.PARTIALLY_RECEIVED,
            PharmacyRefillRequestStatus.ACKNOWLEDGED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Refill request is not approved for issue preparation",
            )

        store_unit = self._get_store_unit(
            clinic_id=clinic_id,
            store_unit_id=payload.store_unit_id,
        )

        request_items = self._get_refill_request_items(request.id)
        request_item_by_id = {item.id: item for item in request_items}
        self._rebalance_reservations(clinic_id=clinic_id)
        inventory_ids = {item.inventory_item_id for item in request_items}
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == clinic_id,
                PharmacyInventoryItem.id.in_(inventory_ids),
            )
            .with_for_update()
            .all()
        )
        inventory_map = {item.id: item for item in inventory_items}

        voucher = PharmacyIssueVoucher(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            voucher_number=self._next_voucher_number(clinic_id=clinic_id),
            store_unit_id=store_unit.id,
            receiving_unit_id=request.requesting_unit_id,
            refill_request_id=request.id,
            status=PharmacyIssueVoucherStatus.PREPARED,
            prepared_by=actor.id,
            prepared_at=datetime.now(timezone.utc),
            approved_by=request.reviewed_by,
            note=payload.note or None,
        )
        self.db.add(voucher)
        self.db.flush()

        total_prepared = 0
        for item_payload in payload.items:
            request_item = request_item_by_id.get(item_payload.refill_request_item_id)
            if request_item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Issue voucher item references an unknown refill request item",
                )
            if request_item.approved_quantity is None or request_item.approved_quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot issue stock for a refill item without approval",
                )
            remaining_approved_balance = max(
                (request_item.approved_quantity or 0) - request_item.issued_quantity,
                0,
            )
            if item_payload.issued_quantity > remaining_approved_balance:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Prepared quantity exceeds remaining approved balance for this request item",
                )

            inventory_item = inventory_map[request_item.inventory_item_id]
            store_lot = self._find_store_lot(
                store_unit_id=store_unit.id,
                inventory_item_id=inventory_item.id,
                batch_number=item_payload.batch_number,
                expiry_date=item_payload.expiry_date,
            )
            if store_lot is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Store batch not found for issue preparation",
                )
            if store_lot.quantity_on_hand < item_payload.issued_quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Store batch does not have enough stock for issue preparation",
                )
            self.db.add(
                PharmacyIssueVoucherItem(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    voucher_id=voucher.id,
                    refill_request_item_id=request_item.id,
                    inventory_item_id=inventory_item.id,
                    batch_number=item_payload.batch_number,
                    expiry_date=item_payload.expiry_date,
                    issued_quantity=item_payload.issued_quantity,
                )
            )
            total_prepared += item_payload.issued_quantity

        if total_prepared <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Issue voucher must contain at least one prepared quantity",
            )

        request.status = PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS
        self.db.add(request)
        EventService(self.db).build_event(
            event_type="PHARMACY_ISSUE_VOUCHER_GENERATED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "voucher_id": str(voucher.id),
                "voucher_number": voucher.voucher_number,
                "refill_request_id": str(request.id),
                "receiving_unit_id": str(request.requesting_unit_id),
                "prepared_quantity_total": total_prepared,
            },
        )
        self.db.commit()
        return self.get_issue_voucher(clinic_id=clinic_id, voucher_id=voucher.id)

    def dispatch_issue_voucher(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        voucher_id: UUID,
        payload,
    ) -> dict:
        voucher = self._get_issue_voucher(clinic_id=clinic_id, voucher_id=voucher_id)
        if voucher.status not in {
            PharmacyIssueVoucherStatus.DRAFT,
            PharmacyIssueVoucherStatus.PREPARED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only prepared issue vouchers can be dispatched",
            )

        request = None
        if voucher.refill_request_id:
            request = self._get_refill_request(
                clinic_id=clinic_id,
                request_id=voucher.refill_request_id,
            )

        store_unit = self._get_store_unit(
            clinic_id=clinic_id,
            store_unit_id=voucher.store_unit_id,
        )
        voucher_items = self._get_issue_voucher_items(voucher.id)
        if not voucher_items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cannot dispatch an empty issue voucher",
            )

        request_items = (
            {
                item.id: item
                for item in self._get_refill_request_items(voucher.refill_request_id)
            }
            if voucher.refill_request_id
            else {}
        )
        inventory_ids = {item.inventory_item_id for item in voucher_items}
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == clinic_id,
                PharmacyInventoryItem.id.in_(inventory_ids),
            )
            .with_for_update()
            .all()
        )
        inventory_map = {item.id: item for item in inventory_items}

        total_dispatched = 0
        for voucher_item in voucher_items:
            inventory_item = inventory_map.get(voucher_item.inventory_item_id)
            if inventory_item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Voucher item references unknown inventory",
                )
            store_lot = self._find_store_lot(
                store_unit_id=store_unit.id,
                inventory_item_id=voucher_item.inventory_item_id,
                batch_number=voucher_item.batch_number,
                expiry_date=voucher_item.expiry_date,
            )
            if store_lot is None or store_lot.quantity_on_hand < voucher_item.issued_quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Store batch does not have enough stock for dispatch",
                )
            if inventory_item.stock_quantity < voucher_item.issued_quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Central store stock is insufficient for dispatch",
                )

            store_lot.quantity_on_hand -= voucher_item.issued_quantity
            self.db.add(store_lot)

            stock_before = inventory_item.stock_quantity
            inventory_item.stock_quantity -= voucher_item.issued_quantity
            self.db.add(inventory_item)
            self.db.add(
                PharmacyStockMovement(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    inventory_item_id=inventory_item.id,
                    service_line_id=store_unit.id,
                    actor_id=actor.id,
                    movement_type="ISSUE",
                    quantity_delta=-voucher_item.issued_quantity,
                    stock_before=stock_before,
                    stock_after=inventory_item.stock_quantity,
                    note=f"Issue Voucher {voucher.voucher_number}",
                    reference_type="ISSUE_VOUCHER",
                    reference_id=voucher.id,
                )
            )

            request_item = request_items.get(voucher_item.refill_request_item_id)
            if request_item is not None:
                request_item.reserved_quantity = max(
                    request_item.reserved_quantity - voucher_item.issued_quantity,
                    0,
                )
                request_item.issued_quantity += voucher_item.issued_quantity
                self.db.add(request_item)
            total_dispatched += voucher_item.issued_quantity

        voucher.status = PharmacyIssueVoucherStatus.DISPATCHED
        voucher.issued_by = actor.id
        voucher.issued_at = datetime.now(timezone.utc)
        voucher.dispatched_by = actor.id
        voucher.dispatched_at = voucher.issued_at
        if payload.note:
            voucher.note = (
                f"{voucher.note}\nDispatch note: {payload.note}"
                if voucher.note
                else f"Dispatch note: {payload.note}"
            )
        self.db.add(voucher)

        if request is not None:
            request.status = self._recalculate_refill_request_status(request.id)
            self.db.add(request)

        EventService(self.db).build_event(
            event_type="PHARMACY_ISSUE_DISPATCHED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "voucher_id": str(voucher.id),
                "voucher_number": voucher.voucher_number,
                "refill_request_id": str(request.id) if request is not None else None,
                "receiving_unit_id": str(voucher.receiving_unit_id),
                "issued_quantity_total": total_dispatched,
            },
        )
        self.db.commit()
        return self.get_issue_voucher(clinic_id=clinic_id, voucher_id=voucher.id)

    def issue_stock(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        payload,
    ) -> dict:
        return self.create_issue_voucher(
            clinic_id=clinic_id,
            actor=actor,
            payload=payload,
        )

    def acknowledge_issue_voucher(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        voucher_id: UUID,
        payload,
    ) -> dict:
        receiving_unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=getattr(payload, "unit_id", None),
        )
        voucher = self._get_issue_voucher(clinic_id=clinic_id, voucher_id=voucher_id)
        if voucher.receiving_unit_id != receiving_unit.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Issue voucher is outside your receiving unit scope",
            )
        if voucher.status == PharmacyIssueVoucherStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cancelled issue vouchers cannot be acknowledged",
            )
        if voucher.status not in {
            PharmacyIssueVoucherStatus.DISPATCHED,
            PharmacyIssueVoucherStatus.PARTIALLY_RECEIVED,
            PharmacyIssueVoucherStatus.ISSUED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Voucher must be dispatched before acknowledgement",
            )

        voucher_items = self._get_issue_voucher_items(voucher.id)
        voucher_item_by_id = {item.id: item for item in voucher_items}
        refill_request_items = {
            item.id: item
            for item in self._get_refill_request_items(voucher.refill_request_id)
        } if voucher.refill_request_id else {}

        total_received = 0
        for item_payload in payload.items:
            voucher_item = voucher_item_by_id.get(item_payload.voucher_item_id)
            if voucher_item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Acknowledgement references an unknown voucher item",
                )
            remaining = voucher_item.issued_quantity - voucher_item.received_quantity
            if item_payload.received_quantity > remaining:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Received quantity exceeds issued balance",
                )
            if item_payload.received_quantity == 0:
                continue

            lot = (
                self.db.query(PharmacyUnitStockLot)
                .filter(
                    PharmacyUnitStockLot.clinic_id == clinic_id,
                    PharmacyUnitStockLot.service_line_id == receiving_unit.id,
                    PharmacyUnitStockLot.inventory_item_id == voucher_item.inventory_item_id,
                    PharmacyUnitStockLot.batch_number == voucher_item.batch_number,
                    PharmacyUnitStockLot.expiry_date == voucher_item.expiry_date,
                )
                .with_for_update()
                .first()
            )
            if lot is None:
                lot = PharmacyUnitStockLot(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    service_line_id=receiving_unit.id,
                    inventory_item_id=voucher_item.inventory_item_id,
                    batch_number=voucher_item.batch_number,
                    expiry_date=voucher_item.expiry_date,
                    quantity_on_hand=0,
                )
            stock_before = lot.quantity_on_hand
            lot.quantity_on_hand += item_payload.received_quantity
            self.db.add(lot)

            self.db.add(
                PharmacyStockMovement(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    inventory_item_id=voucher_item.inventory_item_id,
                    service_line_id=receiving_unit.id,
                    actor_id=actor.id,
                    movement_type="RECEIVE",
                    quantity_delta=item_payload.received_quantity,
                    stock_before=stock_before,
                    stock_after=lot.quantity_on_hand,
                    note=f"Issue Voucher {voucher.voucher_number}",
                    reference_type="ISSUE_VOUCHER",
                    reference_id=voucher.id,
                )
            )
            voucher_item.received_quantity += item_payload.received_quantity
            self.db.add(voucher_item)
            if voucher_item.refill_request_item_id and voucher_item.refill_request_item_id in refill_request_items:
                refill_item = refill_request_items[voucher_item.refill_request_item_id]
                refill_item.received_quantity += item_payload.received_quantity
                self.db.add(refill_item)
            total_received += item_payload.received_quantity

        if total_received <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Acknowledgement must confirm at least one received quantity",
            )

        voucher.acknowledged_by = actor.id
        voucher.acknowledged_at = datetime.now(timezone.utc)
        if payload.note:
            voucher.note = (
                f"{voucher.note}\nReceipt note: {payload.note}"
                if voucher.note
                else f"Receipt note: {payload.note}"
            )
        voucher.status = self._recalculate_issue_voucher_status(voucher.id)
        if voucher.status in {
            PharmacyIssueVoucherStatus.RECEIVED,
            PharmacyIssueVoucherStatus.ACKNOWLEDGED,
        }:
            voucher.closed_at = datetime.now(timezone.utc)
        self.db.add(voucher)

        if voucher.refill_request_id:
            request = self._get_refill_request(
                clinic_id=clinic_id,
                request_id=voucher.refill_request_id,
            )
            request.status = self._recalculate_refill_request_status(request.id)
            self.db.add(request)

        EventService(self.db).build_event(
            event_type="PHARMACY_ACKNOWLEDGEMENT_RECORDED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "voucher_id": str(voucher.id),
                "voucher_number": voucher.voucher_number,
                "receiving_unit_id": str(receiving_unit.id),
                "received_quantity_total": total_received,
            },
        )
        self.db.commit()
        return self.get_issue_voucher(clinic_id=clinic_id, voucher_id=voucher.id)

    def list_unit_return_requests(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        selected_unit_id: UUID | None = None,
    ) -> list[dict]:
        returning_unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=selected_unit_id,
        )
        rows = (
            self.db.query(PharmacyReturnRequest)
            .filter(
                PharmacyReturnRequest.clinic_id == clinic_id,
                PharmacyReturnRequest.returning_unit_id == returning_unit.id,
            )
            .order_by(PharmacyReturnRequest.requested_at.desc())
            .all()
        )
        return self._serialize_return_requests(rows)

    def list_store_return_requests(
        self,
        *,
        clinic_id: UUID,
        store_unit_id: UUID,
    ) -> list[dict]:
        rows = (
            self.db.query(PharmacyReturnRequest)
            .filter(
                PharmacyReturnRequest.clinic_id == clinic_id,
                PharmacyReturnRequest.store_unit_id == store_unit_id,
            )
            .order_by(PharmacyReturnRequest.requested_at.desc())
            .all()
        )
        return self._serialize_return_requests(rows)

    def get_return_request(self, *, clinic_id: UUID, return_request_id: UUID) -> dict:
        request = self._get_return_request(
            clinic_id=clinic_id,
            return_request_id=return_request_id,
        )
        return self._serialize_return_requests([request])[0]

    def create_return_request(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        payload,
    ) -> dict:
        returning_unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=getattr(payload, "unit_id", None),
        )
        voucher = self._get_issue_voucher(
            clinic_id=clinic_id,
            voucher_id=payload.issue_voucher_id,
        )
        if voucher.receiving_unit_id != returning_unit.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Issue voucher is outside your unit scope",
            )
        if voucher.status not in {
            PharmacyIssueVoucherStatus.ACKNOWLEDGED,
            PharmacyIssueVoucherStatus.RECEIVED,
            PharmacyIssueVoucherStatus.CLOSED,
            PharmacyIssueVoucherStatus.PARTIALLY_RECEIVED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only acknowledged store issues can be returned to store",
            )

        voucher_item = self._get_issue_voucher_item(
            voucher_id=voucher.id,
            voucher_item_id=payload.issue_voucher_item_id,
        )
        requested_quantity = int(payload.quantity_now_returned)
        if requested_quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Return quantity must be greater than zero",
            )

        eligible_quantity, quantity_already_returned = self._calculate_return_eligibility(
            clinic_id=clinic_id,
            voucher_item=voucher_item,
            returning_unit_id=returning_unit.id,
        )
        if requested_quantity > eligible_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Return quantity exceeds the eligible issued balance for this stock line",
            )
        reason_code = PharmacyReturnReasonCode(self._enum_value(payload.reason_code))

        return_request = PharmacyReturnRequest(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            issue_voucher_id=voucher.id,
            issue_voucher_item_id=voucher_item.id,
            refill_request_id=voucher.refill_request_id,
            store_unit_id=voucher.store_unit_id,
            returning_unit_id=returning_unit.id,
            inventory_item_id=voucher_item.inventory_item_id,
            batch_number=voucher_item.batch_number,
            expiry_date=voucher_item.expiry_date,
            original_issued_quantity=int(voucher_item.received_quantity),
            quantity_already_returned=quantity_already_returned,
            quantity_requested=requested_quantity,
            quantity_received=0,
            remaining_issued_balance=max(eligible_quantity - requested_quantity, 0),
            reason_code=reason_code,
            reason_note=payload.reason_note or None,
            status=PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW,
            requested_by=actor.id,
            requested_at=datetime.now(timezone.utc),
        )
        self.db.add(return_request)

        EventService(self.db).build_event(
            event_type="STORE_RETURN_REQUESTED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "return_request_id": str(return_request.id),
                "issue_voucher_id": str(voucher.id),
                "issue_voucher_number": voucher.voucher_number,
                "issue_voucher_item_id": str(voucher_item.id),
                "returning_unit_id": str(returning_unit.id),
                "store_unit_id": str(voucher.store_unit_id),
                "inventory_item_id": str(voucher_item.inventory_item_id),
                "quantity_requested": requested_quantity,
                "reason_code": reason_code.value,
            },
        )
        self.db.commit()
        return self.get_return_request(
            clinic_id=clinic_id,
            return_request_id=return_request.id,
        )

    def review_return_request(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        return_request_id: UUID,
        payload,
    ) -> dict:
        return_request = self._get_return_request(
            clinic_id=clinic_id,
            return_request_id=return_request_id,
        )
        if return_request.status not in {
            PharmacyReturnRequestStatus.RETURN_REQUESTED,
            PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending return requests can be reviewed",
            )

        voucher = self._get_issue_voucher(
            clinic_id=clinic_id,
            voucher_id=return_request.issue_voucher_id,
        )
        voucher_item = self._get_issue_voucher_item(
            voucher_id=voucher.id,
            voucher_item_id=return_request.issue_voucher_item_id,
        )

        decision = str(payload.decision).upper()
        reviewed_at = datetime.now(timezone.utc)
        return_request.reviewed_by = actor.id
        return_request.reviewed_at = reviewed_at
        return_request.review_note = payload.review_note or None

        if decision == "REJECT":
            return_request.status = PharmacyReturnRequestStatus.RETURN_REJECTED
            return_request.closed_at = reviewed_at
            event_type = "STORE_RETURN_REJECTED"
        else:
            eligible_quantity, quantity_already_returned = self._calculate_return_eligibility(
                clinic_id=clinic_id,
                voucher_item=voucher_item,
                returning_unit_id=return_request.returning_unit_id,
                exclude_return_request_id=return_request.id,
            )
            if return_request.quantity_requested > eligible_quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Return request is no longer eligible for the requested quantity",
                )
            return_request.quantity_already_returned = quantity_already_returned
            return_request.remaining_issued_balance = max(
                eligible_quantity - return_request.quantity_requested,
                0,
            )
            return_request.status = PharmacyReturnRequestStatus.RETURN_ACCEPTED
            event_type = "STORE_RETURN_ACCEPTED"

        self.db.add(return_request)
        EventService(self.db).build_event(
            event_type=event_type,
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "return_request_id": str(return_request.id),
                "issue_voucher_id": str(return_request.issue_voucher_id),
                "issue_voucher_number": voucher.voucher_number,
                "returning_unit_id": str(return_request.returning_unit_id),
                "store_unit_id": str(return_request.store_unit_id),
                "quantity_requested": int(return_request.quantity_requested),
            },
        )
        self.db.commit()
        return self.get_return_request(
            clinic_id=clinic_id,
            return_request_id=return_request.id,
        )

    def receive_return_request(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        return_request_id: UUID,
        payload,
    ) -> dict:
        return_request = self._get_return_request(
            clinic_id=clinic_id,
            return_request_id=return_request_id,
        )
        if return_request.status != PharmacyReturnRequestStatus.RETURN_ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only accepted return requests can be received into store",
            )

        voucher = self._get_issue_voucher(
            clinic_id=clinic_id,
            voucher_id=return_request.issue_voucher_id,
        )
        voucher_item = self._get_issue_voucher_item(
            voucher_id=voucher.id,
            voucher_item_id=return_request.issue_voucher_item_id,
        )
        inventory_item = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == clinic_id,
                PharmacyInventoryItem.id == return_request.inventory_item_id,
            )
            .with_for_update()
            .first()
        )
        if inventory_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Return request references unknown inventory",
            )

        eligible_quantity, quantity_already_returned = self._calculate_return_eligibility(
            clinic_id=clinic_id,
            voucher_item=voucher_item,
            returning_unit_id=return_request.returning_unit_id,
            exclude_return_request_id=return_request.id,
        )
        if return_request.quantity_requested > eligible_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Return request can no longer be received for the requested quantity",
            )

        unit_lot = (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.clinic_id == clinic_id,
                PharmacyUnitStockLot.service_line_id == return_request.returning_unit_id,
                PharmacyUnitStockLot.inventory_item_id == return_request.inventory_item_id,
                PharmacyUnitStockLot.batch_number == return_request.batch_number,
                PharmacyUnitStockLot.expiry_date == return_request.expiry_date,
            )
            .with_for_update()
            .first()
        )
        if unit_lot is None or unit_lot.quantity_on_hand < return_request.quantity_requested:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Returning unit no longer holds enough eligible stock for this return",
            )

        store_lot = self._find_store_lot(
            store_unit_id=return_request.store_unit_id,
            inventory_item_id=return_request.inventory_item_id,
            batch_number=return_request.batch_number,
            expiry_date=return_request.expiry_date,
        )
        if store_lot is None:
            store_lot = PharmacyUnitStockLot(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                service_line_id=return_request.store_unit_id,
                inventory_item_id=return_request.inventory_item_id,
                batch_number=return_request.batch_number,
                expiry_date=return_request.expiry_date,
                quantity_on_hand=0,
            )

        unit_stock_before = unit_lot.quantity_on_hand
        unit_lot.quantity_on_hand -= return_request.quantity_requested
        self.db.add(unit_lot)

        stock_before = inventory_item.stock_quantity
        inventory_item.stock_quantity += return_request.quantity_requested
        inventory_item.last_restocked_at = datetime.now(timezone.utc)
        inventory_item.updated_by = actor.id
        self.db.add(inventory_item)

        store_lot.quantity_on_hand += return_request.quantity_requested
        self.db.add(store_lot)

        self.db.add(
            PharmacyStockMovement(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                inventory_item_id=return_request.inventory_item_id,
                service_line_id=return_request.returning_unit_id,
                actor_id=actor.id,
                movement_type="RETURN",
                quantity_delta=-return_request.quantity_requested,
                stock_before=unit_stock_before,
                stock_after=unit_lot.quantity_on_hand,
                note=f"Return Request {self._return_number(return_request)}",
                reference_type="RETURN_REQUEST",
                reference_id=return_request.id,
            )
        )
        self.db.add(
            PharmacyStockMovement(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                inventory_item_id=return_request.inventory_item_id,
                service_line_id=return_request.store_unit_id,
                actor_id=actor.id,
                movement_type="RETURN",
                quantity_delta=return_request.quantity_requested,
                stock_before=stock_before,
                stock_after=inventory_item.stock_quantity,
                note=f"Issue Voucher {voucher.voucher_number}",
                reference_type="RETURN_REQUEST",
                reference_id=return_request.id,
            )
        )

        now = datetime.now(timezone.utc)
        return_request.quantity_already_returned = quantity_already_returned
        return_request.remaining_issued_balance = max(
            eligible_quantity - return_request.quantity_requested,
            0,
        )
        return_request.quantity_received = return_request.quantity_requested
        return_request.received_by = actor.id
        return_request.received_at = now
        return_request.receive_note = payload.receive_note or None
        return_request.status = PharmacyReturnRequestStatus.RETURN_RECEIVED
        return_request.closed_at = now
        self.db.add(return_request)

        EventService(self.db).build_event(
            event_type="STORE_RETURN_RECEIVED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "return_request_id": str(return_request.id),
                "issue_voucher_id": str(return_request.issue_voucher_id),
                "issue_voucher_number": voucher.voucher_number,
                "returning_unit_id": str(return_request.returning_unit_id),
                "store_unit_id": str(return_request.store_unit_id),
                "inventory_item_id": str(return_request.inventory_item_id),
                "quantity_received": int(return_request.quantity_received),
            },
        )
        self.db.commit()
        return self.get_return_request(
            clinic_id=clinic_id,
            return_request_id=return_request.id,
        )

    def _serialize_refill_requests(
        self,
        requests: list[PharmacyRefillRequest],
    ) -> list[dict]:
        if not requests:
            return []
        request_ids = [row.id for row in requests]
        unit_ids = {row.requesting_unit_id for row in requests}
        user_ids = {row.requested_by for row in requests}
        user_ids.update({row.reviewed_by for row in requests if row.reviewed_by is not None})
        items = (
            self.db.query(PharmacyRefillRequestItem)
            .filter(PharmacyRefillRequestItem.refill_request_id.in_(request_ids))
            .all()
        )
        inventory_ids = {item.inventory_item_id for item in items}
        units = (
            self.db.query(ServiceLine)
            .filter(ServiceLine.id.in_(unit_ids))
            .all()
        )
        users = self.db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(PharmacyInventoryItem.id.in_(inventory_ids))
            .all()
            if inventory_ids
            else []
        )
        items_by_request: dict[UUID, list[PharmacyRefillRequestItem]] = {}
        for item in items:
            items_by_request.setdefault(item.refill_request_id, []).append(item)
        unit_map = {unit.id: unit.name for unit in units}
        user_map = {user.id: user.full_name for user in users}
        inventory_map = {item.id: item.generic_name for item in inventory_items}

        payload: list[dict] = []
        for request in requests:
            payload.append(
                {
                    "id": request.id,
                    "clinic_id": request.clinic_id,
                    "requesting_unit_id": request.requesting_unit_id,
                    "requesting_unit_name": unit_map.get(request.requesting_unit_id, "Unknown unit"),
                    "requested_by": request.requested_by,
                    "requested_by_name": user_map.get(request.requested_by),
                    "request_type": request.request_type,
                    "status": request.status,
                    "urgency": request.urgency,
                    "note": request.note,
                    "reviewed_by": request.reviewed_by,
                    "reviewed_by_name": user_map.get(request.reviewed_by) if request.reviewed_by else None,
                    "reviewed_at": request.reviewed_at,
                    "review_note": request.review_note,
                    "hod_visible_at": request.hod_visible_at,
                    "requested_at": request.requested_at,
                    "requester_timeline": self._request_timeline(request.status),
                    "items": [
                        {
                            "id": item.id,
                            "inventory_item_id": item.inventory_item_id,
                            "inventory_item_name": inventory_map.get(item.inventory_item_id, "Unknown item"),
                            "requested_quantity": item.requested_quantity,
                            "approved_quantity": item.approved_quantity,
                            "reserved_quantity": item.reserved_quantity,
                            "issued_quantity": item.issued_quantity,
                            "received_quantity": item.received_quantity,
                            "note": item.note,
                        }
                        for item in items_by_request.get(request.id, [])
                    ],
                }
            )
        return payload

    def _serialize_issue_vouchers(
        self,
        vouchers: list[PharmacyIssueVoucher],
    ) -> list[dict]:
        if not vouchers:
            return []
        voucher_ids = [voucher.id for voucher in vouchers]
        unit_ids = {
            voucher.store_unit_id for voucher in vouchers
        } | {voucher.receiving_unit_id for voucher in vouchers}
        user_ids = {voucher.issued_by for voucher in vouchers if voucher.issued_by is not None}
        user_ids.update({voucher.prepared_by for voucher in vouchers if voucher.prepared_by is not None})
        user_ids.update({voucher.approved_by for voucher in vouchers if voucher.approved_by is not None})
        user_ids.update({voucher.dispatched_by for voucher in vouchers if voucher.dispatched_by is not None})
        user_ids.update({voucher.acknowledged_by for voucher in vouchers if voucher.acknowledged_by is not None})
        voucher_items = (
            self.db.query(PharmacyIssueVoucherItem)
            .filter(PharmacyIssueVoucherItem.voucher_id.in_(voucher_ids))
            .all()
        )
        inventory_ids = {item.inventory_item_id for item in voucher_items}
        units = self.db.query(ServiceLine).filter(ServiceLine.id.in_(unit_ids)).all()
        users = self.db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(PharmacyInventoryItem.id.in_(inventory_ids))
            .all()
            if inventory_ids
            else []
        )
        items_by_voucher: dict[UUID, list[PharmacyIssueVoucherItem]] = {}
        for item in voucher_items:
            items_by_voucher.setdefault(item.voucher_id, []).append(item)
        unit_map = {unit.id: unit.name for unit in units}
        user_map = {user.id: user.full_name for user in users}
        inventory_map = {item.id: item.generic_name for item in inventory_items}

        payload: list[dict] = []
        for voucher in vouchers:
            payload.append(
                {
                    "id": voucher.id,
                    "clinic_id": voucher.clinic_id,
                    "voucher_number": voucher.voucher_number,
                    "store_unit_id": voucher.store_unit_id,
                    "store_unit_name": unit_map.get(voucher.store_unit_id, "Unknown store"),
                    "receiving_unit_id": voucher.receiving_unit_id,
                    "receiving_unit_name": unit_map.get(voucher.receiving_unit_id, "Unknown unit"),
                    "refill_request_id": voucher.refill_request_id,
                    "status": voucher.status,
                    "prepared_by": voucher.prepared_by,
                    "prepared_by_name": user_map.get(voucher.prepared_by) if voucher.prepared_by else None,
                    "prepared_at": voucher.prepared_at,
                    "approved_by": voucher.approved_by,
                    "approved_by_name": user_map.get(voucher.approved_by) if voucher.approved_by else None,
                    "issued_by": voucher.issued_by,
                    "issued_by_name": user_map.get(voucher.issued_by),
                    "issued_at": voucher.issued_at,
                    "dispatched_by": voucher.dispatched_by,
                    "dispatched_at": voucher.dispatched_at,
                    "acknowledged_by": voucher.acknowledged_by,
                    "acknowledged_by_name": user_map.get(voucher.acknowledged_by) if voucher.acknowledged_by else None,
                    "acknowledged_at": voucher.acknowledged_at,
                    "closed_at": voucher.closed_at,
                    "note": voucher.note,
                    "items": [
                        {
                            "id": item.id,
                            "inventory_item_id": item.inventory_item_id,
                            "inventory_item_name": inventory_map.get(item.inventory_item_id, "Unknown item"),
                            "refill_request_item_id": item.refill_request_item_id,
                            "batch_number": item.batch_number,
                            "expiry_date": item.expiry_date,
                            "issued_quantity": item.issued_quantity,
                            "received_quantity": item.received_quantity,
                        }
                        for item in items_by_voucher.get(voucher.id, [])
                    ],
                }
            )
        return payload

    def _serialize_return_requests(
        self,
        return_requests: list[PharmacyReturnRequest],
    ) -> list[dict]:
        if not return_requests:
            return []

        voucher_ids = {row.issue_voucher_id for row in return_requests}
        inventory_ids = {row.inventory_item_id for row in return_requests}
        unit_ids = {row.returning_unit_id for row in return_requests} | {
            row.store_unit_id for row in return_requests
        }
        user_ids = {row.requested_by for row in return_requests}
        user_ids.update({row.reviewed_by for row in return_requests if row.reviewed_by is not None})
        user_ids.update({row.received_by for row in return_requests if row.received_by is not None})

        vouchers = (
            self.db.query(PharmacyIssueVoucher)
            .filter(PharmacyIssueVoucher.id.in_(voucher_ids))
            .all()
        )
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(PharmacyInventoryItem.id.in_(inventory_ids))
            .all()
        )
        units = self.db.query(ServiceLine).filter(ServiceLine.id.in_(unit_ids)).all()
        users = self.db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []

        voucher_map = {voucher.id: voucher for voucher in vouchers}
        inventory_map = {row.id: row.generic_name for row in inventory_items}
        unit_map = {unit.id: unit.name for unit in units}
        user_map = {user.id: user.full_name for user in users}

        payload: list[dict] = []
        for row in return_requests:
            eligible_return_quantity, _ = self._calculate_return_eligibility(
                clinic_id=row.clinic_id,
                voucher_item=self._get_issue_voucher_item(
                    voucher_id=row.issue_voucher_id,
                    voucher_item_id=row.issue_voucher_item_id,
                    lock=False,
                ),
                returning_unit_id=row.returning_unit_id,
            )
            voucher = voucher_map.get(row.issue_voucher_id)
            payload.append(
                {
                    "id": row.id,
                    "return_number": self._return_number(row),
                    "clinic_id": row.clinic_id,
                    "issue_voucher_id": row.issue_voucher_id,
                    "issue_voucher_number": voucher.voucher_number if voucher else "Unknown voucher",
                    "issue_voucher_item_id": row.issue_voucher_item_id,
                    "refill_request_id": row.refill_request_id,
                    "returning_unit_id": row.returning_unit_id,
                    "returning_unit_name": unit_map.get(row.returning_unit_id, "Unknown unit"),
                    "store_unit_id": row.store_unit_id,
                    "store_unit_name": unit_map.get(row.store_unit_id, "Unknown store"),
                    "inventory_item_id": row.inventory_item_id,
                    "inventory_item_name": inventory_map.get(row.inventory_item_id, "Unknown item"),
                    "batch_number": row.batch_number,
                    "expiry_date": row.expiry_date,
                    "original_issued_quantity": int(row.original_issued_quantity),
                    "quantity_already_returned": int(row.quantity_already_returned),
                    "quantity_now_returned": int(row.quantity_requested),
                    "quantity_received": int(row.quantity_received),
                    "remaining_issued_balance": int(row.remaining_issued_balance),
                    "eligible_return_quantity": int(eligible_return_quantity),
                    "reason_code": row.reason_code,
                    "reason_note": row.reason_note,
                    "status": row.status,
                    "requested_by": row.requested_by,
                    "requested_by_name": user_map.get(row.requested_by),
                    "requested_at": self._ensure_utc(row.requested_at),
                    "reviewed_by": row.reviewed_by,
                    "reviewed_by_name": user_map.get(row.reviewed_by) if row.reviewed_by else None,
                    "reviewed_at": self._ensure_utc(row.reviewed_at),
                    "review_note": row.review_note,
                    "received_by": row.received_by,
                    "received_by_name": user_map.get(row.received_by) if row.received_by else None,
                    "received_at": self._ensure_utc(row.received_at),
                    "receive_note": row.receive_note,
                    "closed_at": self._ensure_utc(row.closed_at),
                    "return_timeline": self._return_timeline(
                        status=row.status,
                        closed_at=row.closed_at,
                    ),
                }
            )
        return payload

    def _get_refill_request(self, *, clinic_id: UUID, request_id: UUID) -> PharmacyRefillRequest:
        request = (
            self.db.query(PharmacyRefillRequest)
            .filter(
                PharmacyRefillRequest.clinic_id == clinic_id,
                PharmacyRefillRequest.id == request_id,
            )
            .first()
        )
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refill request not found",
            )
        return request

    def _get_refill_request_items(self, request_id: UUID) -> list[PharmacyRefillRequestItem]:
        return (
            self.db.query(PharmacyRefillRequestItem)
            .filter(PharmacyRefillRequestItem.refill_request_id == request_id)
            .with_for_update()
            .all()
        )

    def _get_issue_voucher(self, *, clinic_id: UUID, voucher_id: UUID) -> PharmacyIssueVoucher:
        voucher = (
            self.db.query(PharmacyIssueVoucher)
            .filter(
                PharmacyIssueVoucher.clinic_id == clinic_id,
                PharmacyIssueVoucher.id == voucher_id,
            )
            .first()
        )
        if voucher is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue voucher not found",
            )
        return voucher

    def _get_issue_voucher_items(self, voucher_id: UUID) -> list[PharmacyIssueVoucherItem]:
        return (
            self.db.query(PharmacyIssueVoucherItem)
            .filter(PharmacyIssueVoucherItem.voucher_id == voucher_id)
            .with_for_update()
            .all()
        )

    def _get_issue_voucher_item(
        self,
        *,
        voucher_id: UUID,
        voucher_item_id: UUID,
        lock: bool = True,
    ) -> PharmacyIssueVoucherItem:
        query = self.db.query(PharmacyIssueVoucherItem).filter(
            PharmacyIssueVoucherItem.voucher_id == voucher_id,
            PharmacyIssueVoucherItem.id == voucher_item_id,
        )
        if lock:
            query = query.with_for_update()
        item = query.first()
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue voucher item not found",
            )
        return item

    def _get_return_request(
        self,
        *,
        clinic_id: UUID,
        return_request_id: UUID,
    ) -> PharmacyReturnRequest:
        request = (
            self.db.query(PharmacyReturnRequest)
            .filter(
                PharmacyReturnRequest.clinic_id == clinic_id,
                PharmacyReturnRequest.id == return_request_id,
            )
            .with_for_update()
            .first()
        )
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Return request not found",
            )
        return request

    def _get_store_unit(self, *, clinic_id: UUID, store_unit_id: UUID) -> ServiceLine:
        row = (
            self.db.query(ServiceLine, PharmacyUnitProfile)
            .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.id == store_unit_id,
                PharmacyUnitProfile.unit_category == PharmacyUnitCategory.STORE,
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store unit not found",
            )
        unit, _ = row
        return unit

    def _find_store_lot(
        self,
        *,
        store_unit_id: UUID,
        inventory_item_id: UUID,
        batch_number: str,
        expiry_date,
    ) -> PharmacyUnitStockLot | None:
        return (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.service_line_id == store_unit_id,
                PharmacyUnitStockLot.inventory_item_id == inventory_item_id,
                PharmacyUnitStockLot.batch_number == batch_number,
                PharmacyUnitStockLot.expiry_date == expiry_date,
            )
            .with_for_update()
            .first()
        )

    def _calculate_return_eligibility(
        self,
        *,
        clinic_id: UUID,
        voucher_item: PharmacyIssueVoucherItem,
        returning_unit_id: UUID,
        exclude_return_request_id: UUID | None = None,
    ) -> tuple[int, int]:
        return_query = self.db.query(PharmacyReturnRequest).filter(
            PharmacyReturnRequest.clinic_id == clinic_id,
            PharmacyReturnRequest.issue_voucher_item_id == voucher_item.id,
            PharmacyReturnRequest.status.notin_(
                [
                    PharmacyReturnRequestStatus.RETURN_REJECTED,
                ]
            ),
        )
        if exclude_return_request_id is not None:
            return_query = return_query.filter(
                PharmacyReturnRequest.id != exclude_return_request_id
            )
        existing_requests = return_query.all()
        quantity_already_returned = sum(
            int(request.quantity_requested) for request in existing_requests
        )

        unit_lot = (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.clinic_id == clinic_id,
                PharmacyUnitStockLot.service_line_id == returning_unit_id,
                PharmacyUnitStockLot.inventory_item_id == voucher_item.inventory_item_id,
                PharmacyUnitStockLot.batch_number == voucher_item.batch_number,
                PharmacyUnitStockLot.expiry_date == voucher_item.expiry_date,
            )
            .first()
        )
        on_hand = max(int(unit_lot.quantity_on_hand), 0) if unit_lot is not None else 0
        issued_balance = max(int(voucher_item.received_quantity) - quantity_already_returned, 0)
        return min(issued_balance, on_hand), quantity_already_returned

    def _recalculate_refill_request_status(self, request_id: UUID) -> PharmacyRefillRequestStatus:
        items = (
            self.db.query(PharmacyRefillRequestItem)
            .filter(PharmacyRefillRequestItem.refill_request_id == request_id)
            .all()
        )
        active_preparation_exists = (
            self.db.query(PharmacyIssueVoucher.id)
            .filter(
                PharmacyIssueVoucher.refill_request_id == request_id,
                PharmacyIssueVoucher.status.in_(
                    {
                        PharmacyIssueVoucherStatus.DRAFT,
                        PharmacyIssueVoucherStatus.PREPARED,
                    }
                ),
            )
            .first()
            is not None
        )
        if not items:
            return PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL
        if all((item.approved_quantity or 0) == 0 for item in items):
            return PharmacyRefillRequestStatus.REJECTED
        approved_complete = all(item.issued_quantity >= (item.approved_quantity or 0) for item in items)
        any_issued = any(item.issued_quantity > 0 for item in items)
        received_complete = all(item.received_quantity >= item.issued_quantity for item in items)
        any_received = any(item.received_quantity > 0 for item in items)
        any_backorder = any(
            max((item.approved_quantity or 0) - item.issued_quantity, 0) > item.reserved_quantity
            for item in items
        )
        if approved_complete and received_complete and any_received:
            return PharmacyRefillRequestStatus.CLOSED
        if any_received:
            return PharmacyRefillRequestStatus.ACKNOWLEDGED
        if approved_complete and any_issued:
            return PharmacyRefillRequestStatus.DISPATCHED
        if any_issued:
            return PharmacyRefillRequestStatus.PARTIALLY_ISSUED
        if any_backorder:
            return PharmacyRefillRequestStatus.BACKORDER_PENDING
        if active_preparation_exists:
            return PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS
        return PharmacyRefillRequestStatus.APPROVED

    def _recalculate_issue_voucher_status(self, voucher_id: UUID) -> PharmacyIssueVoucherStatus:
        items = (
            self.db.query(PharmacyIssueVoucherItem)
            .filter(PharmacyIssueVoucherItem.voucher_id == voucher_id)
            .all()
        )
        if items and all(item.received_quantity >= item.issued_quantity for item in items):
            return PharmacyIssueVoucherStatus.ACKNOWLEDGED
        if any(item.received_quantity > 0 for item in items):
            return PharmacyIssueVoucherStatus.PARTIALLY_RECEIVED
        return PharmacyIssueVoucherStatus.DISPATCHED

    @staticmethod
    def _role_value(role) -> str:
        return getattr(role, "value", str(role))

    @staticmethod
    def _ensure_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _next_voucher_number(self, *, clinic_id: UUID) -> str:
        count = (
            self.db.query(PharmacyIssueVoucher)
            .filter(PharmacyIssueVoucher.clinic_id == clinic_id)
            .count()
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"IV-{stamp}-{count + 1:04d}"

    def _rebalance_reservations(self, *, clinic_id: UUID) -> None:
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(PharmacyInventoryItem.clinic_id == clinic_id)
            .with_for_update()
            .all()
        )
        available_by_inventory_id = {
            item.id: max(int(item.stock_quantity), 0) for item in inventory_items
        }

        requests = (
            self.db.query(PharmacyRefillRequest)
            .filter(
                PharmacyRefillRequest.clinic_id == clinic_id,
                PharmacyRefillRequest.status.in_(self.REQUESTS_WITH_ACTIVE_RESERVATIONS),
            )
            .order_by(PharmacyRefillRequest.requested_at.asc())
            .all()
        )
        if not requests:
            return

        request_items = (
            self.db.query(PharmacyRefillRequestItem)
            .filter(
                PharmacyRefillRequestItem.refill_request_id.in_([request.id for request in requests])
            )
            .with_for_update()
            .all()
        )
        request_by_id = {request.id: request for request in requests}
        request_items.sort(
            key=lambda item: (
                -self._priority_rank(request_by_id[item.refill_request_id].urgency),
                request_by_id[item.refill_request_id].requested_at,
                str(item.id),
            )
        )

        touched_request_ids: set[UUID] = set()
        for item in request_items:
            remaining_requirement = max(
                (item.approved_quantity or 0) - item.issued_quantity,
                0,
            )
            if remaining_requirement <= 0:
                item.reserved_quantity = 0
            else:
                available = available_by_inventory_id.get(item.inventory_item_id, 0)
                reserved = min(remaining_requirement, available)
                item.reserved_quantity = reserved
                available_by_inventory_id[item.inventory_item_id] = available - reserved
            self.db.add(item)
            touched_request_ids.add(item.refill_request_id)

        for request_id in touched_request_ids:
            request = request_by_id.get(request_id)
            if request is None:
                continue
            request.status = self._recalculate_refill_request_status(request_id)
            self.db.add(request)

    @staticmethod
    def _request_timeline(status: PharmacyRefillRequestStatus | str | None) -> list[str]:
        normalized = PharmacySupplyService._enum_value(status)
        timeline = ["Submitted", "Awaiting CMD Approval"]
        if normalized in {
            PharmacyRefillRequestStatus.APPROVED.value,
            PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS.value,
            PharmacyRefillRequestStatus.PARTIALLY_ISSUED.value,
            PharmacyRefillRequestStatus.BACKORDER_PENDING.value,
            PharmacyRefillRequestStatus.DISPATCHED.value,
            PharmacyRefillRequestStatus.ACKNOWLEDGED.value,
            PharmacyRefillRequestStatus.CLOSED.value,
        }:
            timeline.append("Approved")
        if normalized in {
            PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS.value,
            PharmacyRefillRequestStatus.PARTIALLY_ISSUED.value,
            PharmacyRefillRequestStatus.BACKORDER_PENDING.value,
            PharmacyRefillRequestStatus.DISPATCHED.value,
            PharmacyRefillRequestStatus.ACKNOWLEDGED.value,
            PharmacyRefillRequestStatus.CLOSED.value,
        }:
            timeline.append("Store Preparing")
            timeline.append("Voucher Generated")
        if normalized in {
            PharmacyRefillRequestStatus.PARTIALLY_ISSUED.value,
            PharmacyRefillRequestStatus.BACKORDER_PENDING.value,
            PharmacyRefillRequestStatus.DISPATCHED.value,
            PharmacyRefillRequestStatus.ACKNOWLEDGED.value,
            PharmacyRefillRequestStatus.CLOSED.value,
        }:
            timeline.append("Dispatched")
        if normalized in {
            PharmacyRefillRequestStatus.ACKNOWLEDGED.value,
            PharmacyRefillRequestStatus.CLOSED.value,
        }:
            timeline.append("Received")
        if normalized == PharmacyRefillRequestStatus.REJECTED.value:
            timeline.append("Rejected")
        return timeline

    @staticmethod
    def _return_timeline(
        *,
        status: PharmacyReturnRequestStatus | str | None,
        closed_at: datetime | None = None,
    ) -> list[str]:
        normalized = PharmacySupplyService._enum_value(status)
        timeline = ["Submitted", "Pending Store Review"]
        if normalized in {
            PharmacyReturnRequestStatus.RETURN_ACCEPTED.value,
            PharmacyReturnRequestStatus.RETURN_RECEIVED.value,
            PharmacyReturnRequestStatus.RETURN_CLOSED.value,
        }:
            timeline.append("Accepted")
        if normalized == PharmacyReturnRequestStatus.RETURN_REJECTED.value:
            timeline.append("Rejected")
        if normalized in {
            PharmacyReturnRequestStatus.RETURN_RECEIVED.value,
            PharmacyReturnRequestStatus.RETURN_CLOSED.value,
        }:
            timeline.append("Return Received")
        if closed_at is not None or normalized == PharmacyReturnRequestStatus.RETURN_CLOSED.value:
            timeline.append("Closed")
        return timeline

    @staticmethod
    def _return_number(return_request: PharmacyReturnRequest) -> str:
        return f"RT-{return_request.requested_at.strftime('%Y%m%d')}-{str(return_request.id)[:6].upper()}"

    @staticmethod
    def _enum_value(value) -> str:
        return getattr(value, "value", str(value)) if value is not None else ""

    @staticmethod
    def _require_cmd_actor(actor: User) -> None:
        if str(actor.role) != UserRole.CMD.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CMD approval authority is required for this workflow",
            )

    @staticmethod
    def _priority_rank(raw_value: str | None) -> int:
        normalized = (raw_value or "").strip().upper()
        if normalized in {"EMERGENCY", "CRITICAL"}:
            return 3
        if normalized in {"URGENT", "HIGH"}:
            return 2
        return 1
