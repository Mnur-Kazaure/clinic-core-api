from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event_log import EventLog
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_issue_voucher import PharmacyIssueVoucher
from app.models.pharmacy_issue_voucher_item import PharmacyIssueVoucherItem
from app.models.pharmacy_refill_request import PharmacyRefillRequest
from app.models.pharmacy_refill_request_item import PharmacyRefillRequestItem
from app.models.pharmacy_stock_movement import PharmacyStockMovement
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.service_line import ServiceLine
from app.models.user import User
from app.schemas.pharmacy_store import (
    PharmacyStoreActivityRowResponse,
    PharmacyStoreAdjustmentRowResponse,
    PharmacyStoreApprovedRequestRowResponse,
    PharmacyStoreDashboardResponse,
    PharmacyStoreExpiryRiskRowResponse,
    PharmacyStoreInventoryRowResponse,
    PharmacyStoreIssueVoucherItemResponse,
    PharmacyStoreIssueVoucherRowResponse,
    PharmacyStoreMovementRowResponse,
    PharmacyStoreOperationalSummaryRowResponse,
    PharmacyStoreOverviewResponse,
    PharmacyStoreReceiveStockRequest,
    PharmacyStoreReportsAnalyticsResponse,
    PharmacyStoreRequestItemResponse,
    PharmacyStoreStockActionResponse,
    PharmacyStoreTrendRowResponse,
    PharmacyStoreAdjustmentRequest,
)
from app.schemas.pharmacy_supply import PharmacyReturnRequestResponse
from app.services.event_service import EventService
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.shared.enums import (
    PharmacyInventoryClassification,
    PharmacyInventoryTrackingMode,
    PharmacyIssueVoucherStatus,
    PharmacyReturnRequestStatus,
    PharmacyRefillRequestStatus,
    PharmacyRequestType,
    PharmacyUnitCategory,
)


class PharmacyStoreDashboardService:
    MAX_ACTIVITY_ROWS = 60
    EXPIRY_SOON_DAYS = 45

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        store_unit_id: UUID | None = None,
    ) -> PharmacyStoreDashboardResponse:
        start_date, end_date, start_dt, end_dt = self._normalize_date_range(
            start_date=start_date,
            end_date=end_date,
        )
        supply_service = PharmacySupplyService(self.db)
        supply_service.rebalance_reservations(clinic_id=clinic_id)
        self.db.flush()

        store_unit = self._resolve_store_unit(
            clinic_id=clinic_id,
            store_unit_id=store_unit_id,
        )
        generated_at = datetime.now(timezone.utc)

        inventory_items = self._list_inventory_items(clinic_id=clinic_id)
        lots = self._list_store_lots(clinic_id=clinic_id, store_unit_id=store_unit.id)
        requests = self._list_refill_requests(clinic_id=clinic_id)
        request_items = self._list_request_items(
            request_ids=[request.id for request in requests]
        )
        vouchers = self._list_issue_vouchers(
            clinic_id=clinic_id,
            store_unit_id=store_unit.id,
        )
        voucher_items = self._list_voucher_items([voucher.id for voucher in vouchers])
        return_requests = [
            PharmacyReturnRequestResponse.model_validate(row)
            for row in supply_service.list_store_return_requests(
                clinic_id=clinic_id,
                store_unit_id=store_unit.id,
            )
        ]
        movements = self._list_store_movements(
            clinic_id=clinic_id,
            store_unit_id=store_unit.id,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        activity_events = self._list_activity_events(
            clinic_id=clinic_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        inventory_by_id = {item.id: item for item in inventory_items}
        request_by_id = {request.id: request for request in requests}
        user_map = self._load_user_map(
            user_ids={
                request.requested_by
                for request in requests
            }
            | {request.reviewed_by for request in requests if request.reviewed_by}
            | {voucher.prepared_by for voucher in vouchers if voucher.prepared_by}
            | {voucher.issued_by for voucher in vouchers if voucher.issued_by}
            | {voucher.approved_by for voucher in vouchers if voucher.approved_by}
            | {voucher.acknowledged_by for voucher in vouchers if voucher.acknowledged_by}
            | {row.requested_by for row in return_requests}
            | {row.reviewed_by for row in return_requests if row.reviewed_by}
            | {row.received_by for row in return_requests if row.received_by}
            | {movement.actor_id for movement in movements if movement.actor_id}
            | {event.actor_id for event in activity_events if event.actor_id},
        )
        unit_map = self._load_unit_map(
            unit_ids={request.requesting_unit_id for request in requests}
            | {voucher.receiving_unit_id for voucher in vouchers}
            | {store_unit.id}
            | {row.returning_unit_id for row in return_requests}
        )

        request_items_by_request = defaultdict(list)
        reserved_by_inventory = Counter()
        for item in request_items:
            request_items_by_request[item.refill_request_id].append(item)
            reserved_by_inventory[item.inventory_item_id] += max(item.reserved_quantity, 0)

        voucher_items_by_voucher = defaultdict(list)
        for item in voucher_items:
            voucher_items_by_voucher[item.voucher_id].append(item)

        inventory_rows = self._build_inventory_rows(
            inventory_items=inventory_items,
            lots=lots,
            reserved_by_inventory=reserved_by_inventory,
        )
        department_requests = self._build_request_rows(
            requests=requests,
            request_items_by_request=request_items_by_request,
            inventory_by_id=inventory_by_id,
            unit_map=unit_map,
            user_map=user_map,
            generated_at=generated_at,
        )
        approved_requests = [
            row
            for row in department_requests
            if row.status in {
                PharmacyRefillRequestStatus.APPROVED,
                PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS,
                PharmacyRefillRequestStatus.BACKORDER_PENDING,
                PharmacyRefillRequestStatus.PARTIALLY_ISSUED,
                PharmacyRefillRequestStatus.DISPATCHED,
                PharmacyRefillRequestStatus.ACKNOWLEDGED,
            }
        ]
        issue_voucher_rows = self._build_issue_voucher_rows(
            vouchers=vouchers,
            voucher_items_by_voucher=voucher_items_by_voucher,
            request_items_by_request=request_items_by_request,
            unit_map=unit_map,
            user_map=user_map,
            inventory_by_id=inventory_by_id,
        )
        dispatch_receiving = [
            row
            for row in issue_voucher_rows
            if row.awaiting_acknowledgement
            or row.discrepancy_pending
            or row.status
            in {
                PharmacyIssueVoucherStatus.ACKNOWLEDGED,
                PharmacyIssueVoucherStatus.RECEIVED,
            }
        ]
        movement_rows = self._build_movement_rows(
            movements=movements,
            inventory_by_id=inventory_by_id,
            unit_map=unit_map,
            user_map=user_map,
            vouchers=vouchers,
            requests=requests,
            lots=lots,
            return_requests=return_requests,
        )
        expiry_rows = self._build_expiry_rows(
            lots=lots,
            inventory_by_id=inventory_by_id,
        )
        adjustment_rows = [
            PharmacyStoreAdjustmentRowResponse(
                movement_id=row.movement_id,
                occurred_at=row.occurred_at,
                item_name=row.item_name,
                batch_number=row.batch_number,
                quantity_delta=row.quantity_delta,
                actor_name=row.actor_name,
                reason=row.reference_number,
                reference_number=row.reference_number,
            )
            for row in movement_rows
            if row.movement_type == "ADJUSTMENT"
        ]
        activity_rows = self._build_activity_rows(
            events=activity_events,
            movements=movement_rows,
            requests=approved_requests,
            vouchers=issue_voucher_rows,
            return_requests=return_requests,
            user_map=user_map,
            unit_map=unit_map,
        )

        overview = PharmacyStoreOverviewResponse(
            pending_approved_requests=sum(
                1
                for request in approved_requests
                if request.status in {
                    PharmacyRefillRequestStatus.APPROVED,
                    PharmacyRefillRequestStatus.BACKORDER_PENDING,
                    PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS,
                }
            ),
            items_awaiting_issue=sum(
                1
                for request in approved_requests
                for item in request.items
                if item.pending_quantity > 0
            ),
            pending_receiving_acknowledgements=sum(
                1 for row in issue_voucher_rows if row.awaiting_acknowledgement
            ),
            pending_return_reviews=sum(
                1
                for row in return_requests
                if row.status
                in {
                    PharmacyReturnRequestStatus.RETURN_REQUESTED,
                    PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW,
                    PharmacyReturnRequestStatus.RETURN_ACCEPTED,
                }
            ),
            low_stock_items=sum(
                1 for row in inventory_rows if row.stock_status == "LOW_STOCK"
            ),
            expiring_soon_items=sum(
                1
                for row in expiry_rows
                if row.risk_level in {"EXPIRING_SOON", "EXPIRED"}
            ),
            stock_adjustments_pending=len(adjustment_rows),
            currency=self._resolve_currency(inventory_items=inventory_items),
            last_updated_at=generated_at,
        )

        supply_workload = [
            PharmacyStoreOperationalSummaryRowResponse(
                label="Approved requests to issue",
                count=sum(
                    1
                    for row in approved_requests
                    if row.status == PharmacyRefillRequestStatus.APPROVED
                ),
                severity="info",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Partially issued requests",
                count=sum(1 for row in approved_requests if row.status == PharmacyRefillRequestStatus.PARTIALLY_ISSUED),
                severity="warning",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Backordered requests",
                count=sum(1 for row in approved_requests if row.backorder_pending),
                severity="critical" if any(row.backorder_pending for row in approved_requests) else "info",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Longest waiting units",
                count=len({row.requesting_unit_name for row in approved_requests[:3]}),
                detail=", ".join(row.requesting_unit_name for row in approved_requests[:3]) or None,
                severity="warning" if approved_requests else "info",
            ),
        ]
        stock_risk_summary = [
            PharmacyStoreOperationalSummaryRowResponse(
                label="Low stock",
                count=sum(1 for row in inventory_rows if row.stock_status == "LOW_STOCK"),
                severity="warning",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Out of stock",
                count=sum(1 for row in inventory_rows if row.stock_status == "OUT_OF_STOCK"),
                severity="critical",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Near expiry",
                count=sum(1 for row in expiry_rows if row.risk_level == "EXPIRING_SOON"),
                severity="warning",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Expired blocked stock",
                count=sum(1 for row in expiry_rows if row.risk_level == "EXPIRED"),
                severity="critical",
            ),
        ]
        dispatch_status = [
            PharmacyStoreOperationalSummaryRowResponse(
                label="Ready for dispatch",
                count=sum(1 for row in issue_voucher_rows if row.status == PharmacyIssueVoucherStatus.ISSUED),
                severity="info",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Awaiting acknowledgement",
                count=sum(1 for row in issue_voucher_rows if row.awaiting_acknowledgement),
                severity="warning",
            ),
            PharmacyStoreOperationalSummaryRowResponse(
                label="Acknowledged today",
                count=sum(
                    1
                    for row in issue_voucher_rows
                    if row.received_by_name and start_dt <= row.issue_date < end_dt
                ),
                severity="info",
            ),
        ]

        top_consuming_units = self._build_top_consuming_units(issue_voucher_rows)
        reports = self._build_reports(
            movement_rows=movement_rows,
            approved_requests=approved_requests,
            issue_vouchers=issue_voucher_rows,
            top_consuming_units=top_consuming_units,
        )

        return PharmacyStoreDashboardResponse(
            generated_at=generated_at,
            start_date=start_date,
            end_date=end_date,
            store_unit_id=store_unit.id,
            store_unit_name=store_unit.name,
            currency=overview.currency,
            overview=overview,
            supply_workload=supply_workload,
            stock_risk_summary=stock_risk_summary,
            dispatch_status=dispatch_status,
            top_consuming_units=top_consuming_units,
            inventory=inventory_rows,
            department_requests=department_requests,
            approved_requests=approved_requests,
            issue_vouchers=issue_voucher_rows,
            dispatch_receiving=dispatch_receiving,
            return_requests=return_requests,
            movement_history=movement_rows,
            expiry_low_stock=expiry_rows,
            adjustments_reconciliation=adjustment_rows,
            activity_audit=activity_rows,
            reports_analytics=reports,
        )

    def snapshot_signature(self, snapshot: PharmacyStoreDashboardResponse) -> str:
        payload = snapshot.model_dump(mode="json")
        payload["generated_at"] = None
        payload["overview"]["last_updated_at"] = None
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def receive_stock(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        payload: PharmacyStoreReceiveStockRequest,
    ) -> PharmacyStoreStockActionResponse:
        store_unit = self._resolve_store_unit(
            clinic_id=clinic_id,
            store_unit_id=payload.store_unit_id,
        )
        inventory_item = self._get_inventory_item(
            clinic_id=clinic_id,
            inventory_item_id=payload.inventory_item_id,
        )
        if payload.expiry_date is not None and payload.expiry_date < datetime.now(timezone.utc).date():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Expired stock cannot be received into active store inventory",
            )

        lot = (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.clinic_id == clinic_id,
                PharmacyUnitStockLot.service_line_id == store_unit.id,
                PharmacyUnitStockLot.inventory_item_id == inventory_item.id,
                PharmacyUnitStockLot.batch_number == payload.batch_number,
                PharmacyUnitStockLot.expiry_date == payload.expiry_date,
            )
            .with_for_update()
            .first()
        )
        if lot is None:
            lot = PharmacyUnitStockLot(
                id=uuid4(),
                clinic_id=clinic_id,
                service_line_id=store_unit.id,
                inventory_item_id=inventory_item.id,
                batch_number=payload.batch_number,
                expiry_date=payload.expiry_date,
                quantity_on_hand=0,
            )
        lot.quantity_on_hand += payload.quantity_received
        self.db.add(lot)

        stock_before = inventory_item.stock_quantity
        inventory_item.stock_quantity += payload.quantity_received
        inventory_item.last_restocked_at = datetime.now(timezone.utc)
        inventory_item.updated_by = actor.id
        self.db.add(inventory_item)

        reference_number = f"SR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{lot.id.hex[:6].upper()}"
        self.db.add(
            PharmacyStockMovement(
                id=uuid4(),
                clinic_id=clinic_id,
                inventory_item_id=inventory_item.id,
                service_line_id=store_unit.id,
                actor_id=actor.id,
                movement_type="RESTOCK",
                quantity_delta=payload.quantity_received,
                stock_before=stock_before,
                stock_after=inventory_item.stock_quantity,
                note=payload.source_reference_note or "Store stock receipt",
                reference_type="STORE_RECEIPT",
                reference_id=lot.id,
            )
        )
        EventService(self.db).build_event(
            event_type="PHARMACY_STORE_STOCK_RECEIVED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "store_unit_id": str(store_unit.id),
                "inventory_item_id": str(inventory_item.id),
                "batch_number": payload.batch_number,
                "quantity_received": payload.quantity_received,
                "reference_number": reference_number,
            },
        )
        PharmacySupplyService(self.db).rebalance_reservations(clinic_id=clinic_id)
        self.db.commit()
        return PharmacyStoreStockActionResponse(
            inventory_item_id=inventory_item.id,
            item_name=inventory_item.generic_name,
            batch_number=lot.batch_number,
            quantity_on_hand=lot.quantity_on_hand,
            stock_quantity=inventory_item.stock_quantity,
            reference_number=reference_number,
            occurred_at=datetime.now(timezone.utc),
        )

    def adjust_stock(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        payload: PharmacyStoreAdjustmentRequest,
    ) -> PharmacyStoreStockActionResponse:
        if payload.quantity_delta == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="quantity_delta cannot be zero",
            )
        store_unit = self._resolve_store_unit(
            clinic_id=clinic_id,
            store_unit_id=payload.store_unit_id,
        )
        inventory_item = self._get_inventory_item(
            clinic_id=clinic_id,
            inventory_item_id=payload.inventory_item_id,
        )

        lot = None
        if payload.batch_number:
            lot = (
                self.db.query(PharmacyUnitStockLot)
                .filter(
                    PharmacyUnitStockLot.clinic_id == clinic_id,
                    PharmacyUnitStockLot.service_line_id == store_unit.id,
                    PharmacyUnitStockLot.inventory_item_id == inventory_item.id,
                    PharmacyUnitStockLot.batch_number == payload.batch_number,
                    PharmacyUnitStockLot.expiry_date == payload.expiry_date,
                )
                .with_for_update()
                .first()
            )
            if lot is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Store lot not found for adjustment",
                )
            if lot.quantity_on_hand + payload.quantity_delta < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Adjustment would reduce batch stock below zero",
                )
            lot.quantity_on_hand += payload.quantity_delta
            self.db.add(lot)

        if inventory_item.stock_quantity + payload.quantity_delta < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Adjustment would reduce store stock below zero",
            )

        stock_before = inventory_item.stock_quantity
        inventory_item.stock_quantity += payload.quantity_delta
        inventory_item.updated_by = actor.id
        self.db.add(inventory_item)

        reference_number = f"ADJ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{inventory_item.id.hex[:6].upper()}"
        self.db.add(
            PharmacyStockMovement(
                id=uuid4(),
                clinic_id=clinic_id,
                inventory_item_id=inventory_item.id,
                service_line_id=store_unit.id,
                actor_id=actor.id,
                movement_type="ADJUSTMENT",
                quantity_delta=payload.quantity_delta,
                stock_before=stock_before,
                stock_after=inventory_item.stock_quantity,
                note=payload.reason,
                reference_type="STOCK_ADJUSTMENT",
                reference_id=lot.id if lot is not None else inventory_item.id,
            )
        )
        EventService(self.db).build_event(
            event_type="PHARMACY_STORE_ADJUSTMENT_RECORDED",
            actor_id=actor.id,
            actor_role=self._role_value(actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "store_unit_id": str(store_unit.id),
                "inventory_item_id": str(inventory_item.id),
                "quantity_delta": payload.quantity_delta,
                "reference_number": reference_number,
            },
        )
        PharmacySupplyService(self.db).rebalance_reservations(clinic_id=clinic_id)
        self.db.commit()
        return PharmacyStoreStockActionResponse(
            inventory_item_id=inventory_item.id,
            item_name=inventory_item.generic_name,
            batch_number=payload.batch_number,
            quantity_on_hand=lot.quantity_on_hand if lot is not None else inventory_item.stock_quantity,
            stock_quantity=inventory_item.stock_quantity,
            reference_number=reference_number,
            occurred_at=datetime.now(timezone.utc),
        )

    def _normalize_date_range(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date, datetime, datetime]:
        today = datetime.now(timezone.utc).date()
        resolved_start = start_date or end_date or today
        resolved_end = end_date or start_date or today
        if resolved_start > resolved_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="start_date cannot be later than end_date",
            )
        return (
            resolved_start,
            resolved_end,
            datetime.combine(resolved_start, time.min, tzinfo=timezone.utc),
            datetime.combine(resolved_end + timedelta(days=1), time.min, tzinfo=timezone.utc),
        )

    def _resolve_store_unit(
        self,
        *,
        clinic_id: UUID,
        store_unit_id: UUID | None,
    ) -> ServiceLine:
        query = (
            self.db.query(ServiceLine)
            .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                PharmacyUnitProfile.unit_category == PharmacyUnitCategory.STORE,
            )
        )
        if store_unit_id is not None:
            query = query.filter(ServiceLine.id == store_unit_id)
        unit = query.order_by(ServiceLine.name.asc()).first()
        if unit is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pharmacy store unit is configured",
            )
        return unit

    def _get_inventory_item(self, *, clinic_id: UUID, inventory_item_id: UUID) -> PharmacyInventoryItem:
        item = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == clinic_id,
                PharmacyInventoryItem.id == inventory_item_id,
            )
            .with_for_update()
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )
        return item

    def _list_inventory_items(self, *, clinic_id: UUID) -> list[PharmacyInventoryItem]:
        return (
            self.db.query(PharmacyInventoryItem)
            .filter(PharmacyInventoryItem.clinic_id == clinic_id)
            .order_by(PharmacyInventoryItem.generic_name.asc())
            .all()
        )

    def _list_store_lots(self, *, clinic_id: UUID, store_unit_id: UUID) -> list[PharmacyUnitStockLot]:
        return (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.clinic_id == clinic_id,
                PharmacyUnitStockLot.service_line_id == store_unit_id,
            )
            .order_by(PharmacyUnitStockLot.expiry_date.asc().nulls_last())
            .all()
        )

    def _list_refill_requests(self, *, clinic_id: UUID) -> list[PharmacyRefillRequest]:
        return (
            self.db.query(PharmacyRefillRequest)
            .filter(
                PharmacyRefillRequest.clinic_id == clinic_id,
                PharmacyRefillRequest.status.in_(
                    {
                        PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL,
                        PharmacyRefillRequestStatus.APPROVED,
                        PharmacyRefillRequestStatus.ISSUE_PREPARATION_IN_PROGRESS,
                        PharmacyRefillRequestStatus.BACKORDER_PENDING,
                        PharmacyRefillRequestStatus.BACKORDERED,
                        PharmacyRefillRequestStatus.PARTIALLY_ISSUED,
                        PharmacyRefillRequestStatus.DISPATCHED,
                        PharmacyRefillRequestStatus.ACKNOWLEDGED,
                        PharmacyRefillRequestStatus.ISSUED,
                        PharmacyRefillRequestStatus.PARTIALLY_RECEIVED,
                        PharmacyRefillRequestStatus.CLOSED,
                        PharmacyRefillRequestStatus.REJECTED,
                    }
                ),
            )
            .order_by(PharmacyRefillRequest.requested_at.asc())
            .all()
        )

    def _list_request_items(self, request_ids: list[UUID]) -> list[PharmacyRefillRequestItem]:
        if not request_ids:
            return []
        return (
            self.db.query(PharmacyRefillRequestItem)
            .filter(PharmacyRefillRequestItem.refill_request_id.in_(request_ids))
            .all()
        )

    def _list_issue_vouchers(self, *, clinic_id: UUID, store_unit_id: UUID) -> list[PharmacyIssueVoucher]:
        return (
            self.db.query(PharmacyIssueVoucher)
            .filter(
                PharmacyIssueVoucher.clinic_id == clinic_id,
                PharmacyIssueVoucher.store_unit_id == store_unit_id,
            )
            .order_by(PharmacyIssueVoucher.issued_at.desc())
            .all()
        )

    def _list_voucher_items(self, voucher_ids: list[UUID]) -> list[PharmacyIssueVoucherItem]:
        if not voucher_ids:
            return []
        return (
            self.db.query(PharmacyIssueVoucherItem)
            .filter(PharmacyIssueVoucherItem.voucher_id.in_(voucher_ids))
            .all()
        )

    def _list_store_movements(
        self,
        *,
        clinic_id: UUID,
        store_unit_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[PharmacyStockMovement]:
        return (
            self.db.query(PharmacyStockMovement)
            .filter(
                PharmacyStockMovement.clinic_id == clinic_id,
                PharmacyStockMovement.service_line_id == store_unit_id,
                PharmacyStockMovement.occurred_at >= start_dt,
                PharmacyStockMovement.occurred_at < end_dt,
            )
            .order_by(PharmacyStockMovement.occurred_at.desc())
            .all()
        )

    def _list_activity_events(
        self,
        *,
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[EventLog]:
        return (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type.in_(
                    {
                        "PHARMACY_CMD_APPROVED",
                        "PHARMACY_CMD_REJECTED",
                        "PHARMACY_ISSUE_VOUCHER_GENERATED",
                        "PHARMACY_ISSUE_DISPATCHED",
                        "PHARMACY_ACKNOWLEDGEMENT_RECORDED",
                        "PHARMACY_STORE_STOCK_RECEIVED",
                        "PHARMACY_STORE_ADJUSTMENT_RECORDED",
                        "STORE_RETURN_REQUESTED",
                        "STORE_RETURN_ACCEPTED",
                        "STORE_RETURN_REJECTED",
                        "STORE_RETURN_RECEIVED",
                    }
                ),
                EventLog.created_at >= start_dt,
                EventLog.created_at < end_dt,
            )
            .order_by(EventLog.created_at.desc())
            .limit(self.MAX_ACTIVITY_ROWS)
            .all()
        )

    def _build_inventory_rows(
        self,
        *,
        inventory_items: list[PharmacyInventoryItem],
        lots: list[PharmacyUnitStockLot],
        reserved_by_inventory: Counter,
    ) -> list[PharmacyStoreInventoryRowResponse]:
        lots_by_inventory = defaultdict(list)
        for lot in lots:
            lots_by_inventory[lot.inventory_item_id].append(lot)

        rows: list[PharmacyStoreInventoryRowResponse] = []
        for item in inventory_items:
            reserved = int(reserved_by_inventory.get(item.id, 0))
            available = max(int(item.stock_quantity) - reserved, 0)
            item_lots = lots_by_inventory.get(item.id) or [None]
            for lot in item_lots:
                rows.append(
                    PharmacyStoreInventoryRowResponse(
                        inventory_item_id=item.id,
                        item_name=item.generic_name,
                        dosage_form=item.dosage_form,
                        strength=item.strength,
                        classification=PharmacyInventoryClassification(item.classification),
                        tracking_mode=PharmacyInventoryTrackingMode(item.tracking_mode),
                        requires_expiry=bool(item.requires_expiry),
                        category=item.dosage_form,
                        unit_of_measure=item.unit_of_measure,
                        batch_number=lot.batch_number if lot is not None else None,
                        expiry_date=lot.expiry_date if lot is not None else None,
                        quantity_on_hand=int(lot.quantity_on_hand if lot is not None else item.stock_quantity),
                        reserved_quantity=reserved,
                        available_quantity=available,
                        low_stock_threshold=int(item.low_stock_threshold),
                        stock_status=self._stock_status(
                            stock_quantity=int(item.stock_quantity),
                            threshold=int(item.low_stock_threshold),
                        ),
                        currency=item.currency,
                        location_label="Central Store",
                        can_issue=(
                            (lot.quantity_on_hand if lot is not None else item.stock_quantity) > 0
                            and (
                                lot is None
                                or lot.expiry_date is None
                                or lot.expiry_date >= datetime.now(timezone.utc).date()
                            )
                        ),
                    )
                )
        return rows

    def _build_request_rows(
        self,
        *,
        requests: list[PharmacyRefillRequest],
        request_items_by_request: dict[UUID, list[PharmacyRefillRequestItem]],
        inventory_by_id: dict[UUID, PharmacyInventoryItem],
        unit_map: dict[UUID, str],
        user_map: dict[UUID, str],
        generated_at: datetime,
    ) -> list[PharmacyStoreApprovedRequestRowResponse]:
        rows: list[PharmacyStoreApprovedRequestRowResponse] = []
        for request in requests:
            items = request_items_by_request.get(request.id, [])
            requested_at = self._ensure_utc(request.requested_at)
            item_rows = []
            for item in items:
                approved_quantity = int(item.approved_quantity or 0)
                pending_quantity = max(approved_quantity - item.issued_quantity, 0)
                backorder_quantity = max(pending_quantity - item.reserved_quantity, 0)
                item_rows.append(
                    PharmacyStoreRequestItemResponse(
                        refill_request_item_id=item.id,
                        inventory_item_id=item.inventory_item_id,
                        inventory_item_name=(
                            inventory_by_id[item.inventory_item_id].generic_name
                            if item.inventory_item_id in inventory_by_id
                            else "Unknown item"
                        ),
                        requested_quantity=int(item.requested_quantity),
                        approved_quantity=approved_quantity,
                        reserved_quantity=int(item.reserved_quantity),
                        issued_quantity=int(item.issued_quantity),
                        received_quantity=int(item.received_quantity),
                        pending_quantity=pending_quantity,
                        backorder_quantity=backorder_quantity,
                    )
                )
            total_requested = sum(item.requested_quantity for item in items)
            total_reserved = sum(item.reserved_quantity for item in items)
            total_pending = sum(max((item.approved_quantity or 0) - item.issued_quantity, 0) for item in items)
            rows.append(
                PharmacyStoreApprovedRequestRowResponse(
                    request_id=request.id,
                    request_number=self._request_number(request),
                    requesting_unit_id=request.requesting_unit_id,
                    requesting_unit_name=unit_map.get(request.requesting_unit_id, "Unknown unit"),
                    request_type=PharmacyRequestType(request.request_type),
                    requested_at=requested_at,
                    approved_by_name=user_map.get(request.reviewed_by) if request.reviewed_by else None,
                    priority=self._priority_label(request.urgency),
                    status=request.status,
                    item_count=len(items),
                    total_requested_quantity=total_requested,
                    total_reserved_quantity=total_reserved,
                    total_pending_quantity=total_pending,
                    backorder_pending=any(
                        max((item.approved_quantity or 0) - item.issued_quantity, 0) > item.reserved_quantity
                        for item in items
                    ),
                    waiting_minutes=max(int((generated_at - requested_at).total_seconds() // 60), 0),
                    requester_timeline=PharmacySupplyService._request_timeline(request.status),
                    items=item_rows,
                )
            )
        return sorted(
            rows,
            key=lambda row: (
                -self._priority_rank(row.priority),
                row.requested_at,
            ),
        )

    def _build_issue_voucher_rows(
        self,
        *,
        vouchers: list[PharmacyIssueVoucher],
        voucher_items_by_voucher: dict[UUID, list[PharmacyIssueVoucherItem]],
        request_items_by_request: dict[UUID, list[PharmacyRefillRequestItem]],
        unit_map: dict[UUID, str],
        user_map: dict[UUID, str],
        inventory_by_id: dict[UUID, PharmacyInventoryItem],
    ) -> list[PharmacyStoreIssueVoucherRowResponse]:
        request_item_map = {
            item.id: item
            for items in request_items_by_request.values()
            for item in items
        }
        rows: list[PharmacyStoreIssueVoucherRowResponse] = []
        for voucher in vouchers:
            item_rows = []
            pending_quantity = 0
            for item in voucher_items_by_voucher.get(voucher.id, []):
                request_item = request_item_map.get(item.refill_request_item_id)
                requested_quantity = int(request_item.requested_quantity) if request_item else int(item.issued_quantity)
                reserved_quantity = int(request_item.reserved_quantity) if request_item else 0
                pending_item_quantity = max(int(item.issued_quantity) - int(item.received_quantity), 0)
                pending_quantity += pending_item_quantity
                inventory_item = inventory_by_id.get(item.inventory_item_id)
                item_rows.append(
                    PharmacyStoreIssueVoucherItemResponse(
                        voucher_item_id=item.id,
                        inventory_item_id=item.inventory_item_id,
                        inventory_item_name=inventory_item.generic_name if inventory_item else "Unknown item",
                        requested_quantity=requested_quantity,
                        reserved_quantity=reserved_quantity,
                        issued_quantity=int(item.issued_quantity),
                        received_quantity=int(item.received_quantity),
                        pending_quantity=pending_item_quantity,
                        batch_number=item.batch_number,
                        expiry_date=item.expiry_date,
                    )
                )
            rows.append(
                PharmacyStoreIssueVoucherRowResponse(
                    voucher_id=voucher.id,
                    voucher_number=voucher.voucher_number,
                    receiving_unit_id=voucher.receiving_unit_id,
                    receiving_unit_name=unit_map.get(voucher.receiving_unit_id, "Unknown unit"),
                    issue_date=self._ensure_utc(voucher.issued_at),
                    prepared_at=self._ensure_utc(voucher.prepared_at),
                    dispatched_at=self._ensure_utc(voucher.dispatched_at),
                    prepared_by_name=user_map.get(voucher.prepared_by) if voucher.prepared_by else None,
                    issued_by_name=user_map.get(voucher.issued_by),
                    approved_by_name=user_map.get(voucher.approved_by) if voucher.approved_by else None,
                    received_by_name=user_map.get(voucher.acknowledged_by) if voucher.acknowledged_by else None,
                    status=voucher.status,
                    partial_issue=any(
                        request_item_map.get(item.refill_request_item_id)
                        and item.issued_quantity < (request_item_map[item.refill_request_item_id].approved_quantity or item.issued_quantity)
                        for item in voucher_items_by_voucher.get(voucher.id, [])
                    ),
                    pending_quantity=pending_quantity,
                    awaiting_acknowledgement=voucher.status in {
                        PharmacyIssueVoucherStatus.DISPATCHED,
                        PharmacyIssueVoucherStatus.ISSUED,
                        PharmacyIssueVoucherStatus.PARTIALLY_RECEIVED,
                    },
                    discrepancy_pending=any(item.received_quantity < item.issued_quantity for item in voucher_items_by_voucher.get(voucher.id, []))
                    and voucher.status == PharmacyIssueVoucherStatus.PARTIALLY_RECEIVED,
                    items=item_rows,
                )
            )
        return rows

    def _build_movement_rows(
        self,
        *,
        movements: list[PharmacyStockMovement],
        inventory_by_id: dict[UUID, PharmacyInventoryItem],
        unit_map: dict[UUID, str],
        user_map: dict[UUID, str],
        vouchers: list[PharmacyIssueVoucher],
        requests: list[PharmacyRefillRequest],
        lots: list[PharmacyUnitStockLot],
        return_requests: list[PharmacyReturnRequestResponse],
    ) -> list[PharmacyStoreMovementRowResponse]:
        voucher_map = {voucher.id: voucher for voucher in vouchers}
        request_map = {request.id: request for request in requests}
        lot_map = {lot.id: lot for lot in lots}
        return_request_map = {row.id: row for row in return_requests}
        rows: list[PharmacyStoreMovementRowResponse] = []
        for movement in movements:
            reference_number = None
            batch_number = None
            source = None
            destination = None
            if movement.reference_type == "ISSUE_VOUCHER" and movement.reference_id in voucher_map:
                voucher = voucher_map[movement.reference_id]
                reference_number = voucher.voucher_number
                destination = unit_map.get(voucher.receiving_unit_id)
            elif movement.reference_type == "RETURN_REQUEST" and movement.reference_id in return_request_map:
                return_request = return_request_map[movement.reference_id]
                reference_number = return_request.return_number
                batch_number = return_request.batch_number
                source = return_request.returning_unit_name
            elif movement.reference_type == "STORE_RECEIPT" and movement.reference_id in lot_map:
                reference_number = f"SR-{str(movement.reference_id)[:8].upper()}"
                batch_number = lot_map[movement.reference_id].batch_number
            elif movement.reference_type == "STOCK_ADJUSTMENT":
                reference_number = f"ADJ-{str(movement.reference_id)[:8].upper()}"
                if movement.reference_id in lot_map:
                    batch_number = lot_map[movement.reference_id].batch_number

            rows.append(
                PharmacyStoreMovementRowResponse(
                    movement_id=movement.id,
                    occurred_at=self._ensure_utc(movement.occurred_at),
                    movement_type=movement.movement_type,
                    item_name=(
                        inventory_by_id[movement.inventory_item_id].generic_name
                        if movement.inventory_item_id in inventory_by_id
                        else "Unknown item"
                    ),
                    batch_number=batch_number,
                    quantity_delta=int(movement.quantity_delta),
                    source_label=source or "Central Store",
                    destination_label=destination,
                    actor_name=user_map.get(movement.actor_id),
                    reference_number=reference_number,
                    reference_type=movement.reference_type,
                )
            )
        return rows

    def _build_expiry_rows(
        self,
        *,
        lots: list[PharmacyUnitStockLot],
        inventory_by_id: dict[UUID, PharmacyInventoryItem],
    ) -> list[PharmacyStoreExpiryRiskRowResponse]:
        today = datetime.now(timezone.utc).date()
        rows: list[PharmacyStoreExpiryRiskRowResponse] = []
        for lot in lots:
            if lot.quantity_on_hand <= 0:
                continue
            inventory_item = inventory_by_id.get(lot.inventory_item_id)
            if inventory_item is None:
                continue
            risk_level = None
            recommended_action = None
            if lot.quantity_on_hand <= inventory_item.low_stock_threshold:
                risk_level = "LOW_STOCK"
                recommended_action = "Replenish or prioritize approved request allocation"
            if lot.expiry_date is not None:
                if lot.expiry_date < today:
                    risk_level = "EXPIRED"
                    recommended_action = "Block issue and mark for disposal review"
                elif lot.expiry_date <= today + timedelta(days=self.EXPIRY_SOON_DAYS):
                    risk_level = "EXPIRING_SOON"
                    recommended_action = "Prioritize issue or transfer to higher-use unit"
            if risk_level is None:
                continue
            rows.append(
                PharmacyStoreExpiryRiskRowResponse(
                    inventory_item_id=inventory_item.id,
                    item_name=inventory_item.generic_name,
                    batch_number=lot.batch_number,
                    expiry_date=lot.expiry_date,
                    quantity_on_hand=int(lot.quantity_on_hand),
                    risk_level=risk_level,
                    recommended_action=recommended_action or "Review store action",
                )
            )
        return rows

    def _build_activity_rows(
        self,
        *,
        events: list[EventLog],
        movements: list[PharmacyStoreMovementRowResponse],
        requests: list[PharmacyStoreApprovedRequestRowResponse],
        vouchers: list[PharmacyStoreIssueVoucherRowResponse],
        return_requests: list[PharmacyReturnRequestResponse],
        user_map: dict[UUID, str],
        unit_map: dict[UUID, str],
    ) -> list[PharmacyStoreActivityRowResponse]:
        request_number_by_id = {request.request_id: request.request_number for request in requests}
        voucher_number_by_id = {voucher.voucher_id: voucher.voucher_number for voucher in vouchers}
        rows: list[PharmacyStoreActivityRowResponse] = []
        for event in events:
            try:
                payload = json.loads(event.payload or "{}")
            except json.JSONDecodeError:
                payload = {}
            rows.append(
                PharmacyStoreActivityRowResponse(
                    id=str(event.id),
                    occurred_at=self._ensure_utc(event.created_at),
                    action_type=event.event_type,
                    summary=self._activity_summary(event.event_type, payload),
                    detail=payload.get("detail"),
                    item_name=payload.get("item_name"),
                    unit_name=payload.get("receiving_unit_name") or payload.get("requesting_unit_name") or payload.get("returning_unit_name"),
                    voucher_number=voucher_number_by_id.get(UUID(payload["voucher_id"])) if payload.get("voucher_id") else payload.get("voucher_number"),
                    request_number=request_number_by_id.get(UUID(payload["refill_request_id"])) if payload.get("refill_request_id") else None,
                    actor_name=user_map.get(event.actor_id) if event.actor_id else None,
                    severity="critical" if event.event_type in {"PHARMACY_STORE_ADJUSTMENT_RECORDED"} else "info",
                )
            )
        for movement in movements[:20]:
            rows.append(
                PharmacyStoreActivityRowResponse(
                    id=f"movement-{movement.movement_id}",
                    occurred_at=movement.occurred_at,
                    action_type=movement.movement_type,
                    summary=f"{movement.movement_type.title()} {abs(movement.quantity_delta)} {movement.item_name}",
                    detail=movement.reference_number,
                    item_name=movement.item_name,
                    unit_name=movement.destination_label or movement.source_label,
                    voucher_number=movement.reference_number if movement.reference_type == "ISSUE_VOUCHER" else None,
                    request_number=None,
                    actor_name=movement.actor_name,
                    severity="warning" if movement.movement_type == "ADJUSTMENT" else "info",
                )
            )
        for return_request in return_requests[:20]:
            rows.append(
                PharmacyStoreActivityRowResponse(
                    id=f"return-{return_request.id}",
                    occurred_at=return_request.requested_at,
                    action_type=return_request.status.value,
                    summary=f"Return {return_request.return_number} • {return_request.inventory_item_name}",
                    detail=f"{return_request.returning_unit_name} requested {return_request.quantity_now_returned} for {return_request.reason_code.value.replace('_', ' ')}.",
                    item_name=return_request.inventory_item_name,
                    unit_name=return_request.returning_unit_name,
                    voucher_number=return_request.issue_voucher_number,
                    request_number=request_number_by_id.get(return_request.refill_request_id) if return_request.refill_request_id else None,
                    actor_name=return_request.received_by_name or return_request.reviewed_by_name or return_request.requested_by_name,
                    severity="warning" if return_request.status in {PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW, PharmacyReturnRequestStatus.RETURN_ACCEPTED} else "info",
                )
            )
        rows.sort(key=lambda row: row.occurred_at, reverse=True)
        return rows[: self.MAX_ACTIVITY_ROWS]

    def _build_top_consuming_units(
        self,
        issue_voucher_rows: list[PharmacyStoreIssueVoucherRowResponse],
    ) -> list[PharmacyStoreTrendRowResponse]:
        totals = Counter()
        for row in issue_voucher_rows:
            totals[row.receiving_unit_name] += sum(item.issued_quantity for item in row.items)
        return [
            PharmacyStoreTrendRowResponse(label=unit_name, value=value)
            for unit_name, value in totals.most_common(5)
        ]

    def _build_reports(
        self,
        *,
        movement_rows: list[PharmacyStoreMovementRowResponse],
        approved_requests: list[PharmacyStoreApprovedRequestRowResponse],
        issue_vouchers: list[PharmacyStoreIssueVoucherRowResponse],
        top_consuming_units: list[PharmacyStoreTrendRowResponse],
    ) -> PharmacyStoreReportsAnalyticsResponse:
        received_total = sum(
            max(row.quantity_delta, 0)
            for row in movement_rows
            if row.movement_type == "RESTOCK"
        )
        issued_total = sum(
            abs(row.quantity_delta)
            for row in movement_rows
            if row.movement_type == "ISSUE"
        )
        item_totals = Counter()
        stock_out = Counter()
        adjustment_trend = Counter()
        expiry_trend = Counter()
        for row in movement_rows:
            if row.movement_type == "ISSUE":
                item_totals[row.item_name] += abs(row.quantity_delta)
            if row.movement_type == "ADJUSTMENT":
                adjustment_trend["Adjustments"] += 1
        for request in approved_requests:
            if request.backorder_pending:
                stock_out[request.requesting_unit_name] += request.total_pending_quantity
        for voucher in issue_vouchers:
            if voucher.partial_issue:
                adjustment_trend["Partial Issues"] += 1
        return PharmacyStoreReportsAnalyticsResponse(
            stock_received_by_period=received_total,
            stock_issued_by_period=issued_total,
            issue_volume_by_unit=top_consuming_units,
            top_consumed_items=[
                PharmacyStoreTrendRowResponse(label=name, value=value)
                for name, value in item_totals.most_common(5)
            ],
            stock_out_frequency=[
                PharmacyStoreTrendRowResponse(label=name, value=value)
                for name, value in stock_out.most_common(5)
            ],
            expiry_trend=[
                PharmacyStoreTrendRowResponse(label=name, value=value)
                for name, value in expiry_trend.most_common(5)
            ],
            backorder_trend=[
                PharmacyStoreTrendRowResponse(label=request.requesting_unit_name, value=request.total_pending_quantity)
                for request in approved_requests
                if request.backorder_pending
            ],
            adjustment_trend=[
                PharmacyStoreTrendRowResponse(label=name, value=value)
                for name, value in adjustment_trend.items()
            ],
        )

    def _load_user_map(self, *, user_ids: set[UUID]) -> dict[UUID, str]:
        if not user_ids:
            return {}
        rows = self.db.query(User).filter(User.id.in_(user_ids)).all()
        return {row.id: row.full_name for row in rows}

    def _load_unit_map(self, *, unit_ids: set[UUID]) -> dict[UUID, str]:
        if not unit_ids:
            return {}
        rows = self.db.query(ServiceLine).filter(ServiceLine.id.in_(unit_ids)).all()
        return {row.id: row.name for row in rows}

    @staticmethod
    def _resolve_currency(*, inventory_items: list[PharmacyInventoryItem]) -> str:
        return inventory_items[0].currency if inventory_items else "NGN"

    @staticmethod
    def _ensure_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _role_value(role) -> str:
        return getattr(role, "value", str(role))

    @staticmethod
    def _request_number(request: PharmacyRefillRequest) -> str:
        return f"RQ-{request.requested_at.strftime('%Y%m%d')}-{str(request.id)[:6].upper()}"

    @staticmethod
    def _priority_label(raw_value: str | None) -> str:
        normalized = (raw_value or "").strip().upper()
        if normalized in {"EMERGENCY", "CRITICAL"}:
            return "EMERGENCY"
        if normalized in {"URGENT", "HIGH"}:
            return "URGENT"
        return "ROUTINE"

    @classmethod
    def _priority_rank(cls, raw_value: str | None) -> int:
        normalized = cls._priority_label(raw_value)
        if normalized == "EMERGENCY":
            return 3
        if normalized == "URGENT":
            return 2
        return 1

    @staticmethod
    def _stock_status(*, stock_quantity: int, threshold: int) -> str:
        if stock_quantity <= 0:
            return "OUT_OF_STOCK"
        if stock_quantity <= threshold:
            return "LOW_STOCK"
        return "AVAILABLE"

    @staticmethod
    def _activity_summary(event_type: str, payload: dict) -> str:
        summaries = {
            "PHARMACY_CMD_APPROVED": "CMD approved store request",
            "PHARMACY_CMD_REJECTED": "CMD rejected store request",
            "PHARMACY_ISSUE_VOUCHER_GENERATED": "Store generated issue voucher",
            "PHARMACY_ISSUE_DISPATCHED": "Store dispatched issued stock",
            "PHARMACY_ACKNOWLEDGEMENT_RECORDED": "Receiving unit acknowledged stock",
            "PHARMACY_STORE_STOCK_RECEIVED": "Store received stock into central inventory",
            "PHARMACY_STORE_ADJUSTMENT_RECORDED": "Store adjustment recorded",
            "STORE_RETURN_REQUESTED": "Unit requested stock return to store",
            "STORE_RETURN_ACCEPTED": "Store accepted return request",
            "STORE_RETURN_REJECTED": "Store rejected return request",
            "STORE_RETURN_RECEIVED": "Store received returned stock",
        }
        return summaries.get(event_type, event_type.replace("_", " ").title())
