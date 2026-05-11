from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.billing_item import BillingItem
from app.models.cashier_pay_point import CashierPayPoint
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.prescription import Prescription
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.pharmacy_workspace import (
    PharmacyDispensingActivityRowResponse,
    PharmacyDispensingAlertRowResponse,
    PharmacyDispensingDashboardResponse,
    PharmacyDispensingLocalStockRowResponse,
    PharmacyDispensingNextActionResponse,
    PharmacyDispensingOverviewResponse,
    PharmacyDispensingQueueRowResponse,
    PharmacyDispensingReassignmentTargetResponse,
)
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.shared.enums import (
    BillingItemStatus,
    ClinicalPriorityLevel,
    MRNStatus,
    PharmacyExceptionAuthorizationType,
    PharmacyPrescriptionWorkflowStatus,
    PharmacyUnitCategory,
    VisitStatus,
)


TERMINAL_WORKFLOW_STATUSES = {
    PharmacyPrescriptionWorkflowStatus.DISPENSED,
    PharmacyPrescriptionWorkflowStatus.CANCELLED,
    PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED,
}

RELEVANT_QUEUE_STATUSES = {
    PharmacyPrescriptionWorkflowStatus.ASSIGNED,
    PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE,
    PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
    PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
    PharmacyPrescriptionWorkflowStatus.IN_DISPENSE,
}


class PharmacyDispensingDashboardService:
    DISPENSE_DELAY_THRESHOLD_MINUTES = 20
    ACTIVITY_LIMIT = 40
    ALERT_LIMIT = 20

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        selected_unit_id: UUID | None = None,
    ) -> PharmacyDispensingDashboardResponse:
        generated_at = datetime.now(timezone.utc)
        unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=selected_unit_id,
        )

        prescriptions = self._load_prescriptions(clinic_id=clinic_id, unit_id=unit.id)
        visits = self._load_visits({prescription.visit_id for prescription in prescriptions})
        patients = self._load_patients(visits=visits)
        unit_map = self._load_service_line_map(
            {
                unit.id,
                *[visit.service_line_id for visit in visits.values() if visit.service_line_id],
            }
        )
        user_map = self._load_user_map(
            {
                prescription.prescribed_by
                for prescription in prescriptions
            }
            | {
                prescription.dispensed_by
                for prescription in prescriptions
                if prescription.dispensed_by is not None
            }
            | {actor.id}
        )
        billing_map = self._load_billing_map(
            {
                prescription.billing_item_id
                for prescription in prescriptions
                if prescription.billing_item_id is not None
            }
        )
        inventory_map, lots_by_inventory_id, local_stock_rows = self._load_local_stock(
            clinic_id=clinic_id,
            unit_id=unit.id,
            prescriptions=prescriptions,
        )
        pay_point_map = self._load_pay_point_map(
            {
                prescription.assigned_cashier_pay_point_id
                for prescription in prescriptions
                if prescription.assigned_cashier_pay_point_id is not None
            }
        )
        reassignment_events = self._load_reassignment_events(
            clinic_id=clinic_id,
            unit_id=unit.id,
        )

        queue_rows = [
            self._build_queue_row(
                prescription=prescription,
                visit=visits.get(prescription.visit_id),
                patient=patients.get(visits[prescription.visit_id].patient_id) if visits.get(prescription.visit_id) else None,
                patient_mrn=patients.get(visits[prescription.visit_id].patient_id).get('mrn') if visits.get(prescription.visit_id) and patients.get(visits[prescription.visit_id].patient_id) else None,
                source_unit=unit_map.get(visits[prescription.visit_id].service_line_id) if visits.get(prescription.visit_id) and visits[prescription.visit_id].service_line_id else None,
                inventory_item=inventory_map.get(self._inventory_lookup_key(prescription)),
                lots=(
                    lots_by_inventory_id.get(
                        inventory_map.get(self._inventory_lookup_key(prescription)).id,
                        [],
                    )
                    if inventory_map.get(self._inventory_lookup_key(prescription))
                    else []
                ),
                billing_item=billing_map.get(prescription.billing_item_id) if prescription.billing_item_id else None,
                assigned_unit_name=unit.name,
                cashier_pay_point_name=(
                    pay_point_map.get(prescription.assigned_cashier_pay_point_id)
                    if prescription.assigned_cashier_pay_point_id
                    else None
                ),
                user_map=user_map,
                generated_at=generated_at,
                reassignment_event=reassignment_events.get(str(prescription.id)),
            )
            for prescription in prescriptions
        ]

        refill_requests = PharmacySupplyService(self.db).list_unit_refill_requests(
            clinic_id=clinic_id,
            actor=actor,
            selected_unit_id=unit.id,
        )
        issue_vouchers = PharmacySupplyService(self.db).list_unit_issue_vouchers(
            clinic_id=clinic_id,
            actor=actor,
            selected_unit_id=unit.id,
        )
        return_requests = PharmacySupplyService(self.db).list_unit_return_requests(
            clinic_id=clinic_id,
            actor=actor,
            selected_unit_id=unit.id,
        )
        reassignment_targets = self._list_reassignment_targets(
            clinic_id=clinic_id,
            current_unit_id=unit.id,
        )
        alerts = self._build_alerts(
            queue_rows=queue_rows,
            local_stock_rows=local_stock_rows,
            issue_vouchers=issue_vouchers,
            generated_at=generated_at,
        )
        activity_audit = self._build_activity_audit(
            clinic_id=clinic_id,
            unit_id=unit.id,
            queue_rows=queue_rows,
            refill_requests=refill_requests,
            issue_vouchers=issue_vouchers,
            return_requests=return_requests,
            reassignment_events=reassignment_events,
            user_map=user_map,
        )
        overview = self._build_overview(
            queue_rows=queue_rows,
            alerts=alerts,
            generated_at=generated_at,
        )
        next_action = self._build_next_action(
            queue_rows=queue_rows,
            issue_vouchers=issue_vouchers,
            alerts=alerts,
        )

        return PharmacyDispensingDashboardResponse(
            generated_at=generated_at,
            unit_id=unit.id,
            unit_name=unit.name,
            overview=overview,
            next_action=next_action,
            reassignment_targets=reassignment_targets,
            prescriptions=queue_rows,
            local_stock=local_stock_rows,
            refill_requests=refill_requests,
            issue_vouchers=issue_vouchers,
            return_requests=return_requests,
            alerts=alerts,
            activity_audit=activity_audit,
        )

    def snapshot_signature(self, snapshot: PharmacyDispensingDashboardResponse) -> str:
        payload = snapshot.model_dump(mode="json")
        payload["generated_at"] = None
        payload["overview"]["last_updated_at"] = None
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def get_prescription_detail_context(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        selected_unit_id: UUID | None,
        prescription: Prescription,
    ) -> dict:
        unit = PharmacyUnitAccessService(self.db).resolve_selected_unit(
            clinic_id=clinic_id,
            user=actor,
            selected_unit_id=selected_unit_id,
        )
        inventory_item = self._load_inventory_map(
            clinic_id=clinic_id,
            prescriptions=[prescription],
        ).get(self._inventory_lookup_key(prescription))
        lots = self._list_lots_for_inventory_item(
            clinic_id=clinic_id,
            unit_id=unit.id,
            inventory_item_id=inventory_item.id if inventory_item else None,
        )
        available_quantity = sum(lot.quantity_on_hand for lot in lots if not self._lot_is_expired(lot.expiry_date))
        stock_status = self._stock_status_for_lots(
            inventory_item=inventory_item,
            lots=lots,
            available_quantity=available_quantity,
        )
        return {
            'available_stock_lots': [
                {
                    'id': lot.id,
                    'batch_number': lot.batch_number,
                    'expiry_date': lot.expiry_date,
                    'quantity_on_hand': lot.quantity_on_hand,
                    'low_stock': bool(inventory_item and lot.quantity_on_hand <= inventory_item.low_stock_threshold),
                    'blocked': self._lot_is_expired(lot.expiry_date),
                }
                for lot in lots
            ],
            'local_stock_available_quantity': available_quantity,
            'local_stock_status': stock_status,
            'local_stock_source': 'Local Unit Stock',
            'reassignment_targets': self._list_reassignment_targets(
                clinic_id=clinic_id,
                current_unit_id=unit.id,
            ),
        }

    def _build_overview(self, *, queue_rows, alerts, generated_at: datetime) -> PharmacyDispensingOverviewResponse:
        assigned_rows = [row for row in queue_rows if row.readiness_state in RELEVANT_QUEUE_STATUSES]
        return PharmacyDispensingOverviewResponse(
            assigned_prescriptions=len(assigned_rows),
            ready_to_dispense=sum(
                1
                for row in assigned_rows
                if row.readiness_state
                in {
                    PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
                    PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
                }
            ),
            awaiting_payment_clearance=sum(1 for row in assigned_rows if row.readiness_state == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE),
            reassigned=sum(1 for row in assigned_rows if row.recently_reassigned),
            out_of_stock=sum(
                1
                for row in assigned_rows
                if row.local_stock_status in {'OUT_OF_STOCK', 'EXPIRED', 'UNMAPPED'}
            ),
            completed_today=sum(
                1
                for row in queue_rows
                if row.dispensed_at is not None and self._is_same_day(row.dispensed_at, generated_at)
            ),
            last_updated_at=generated_at,
        )

    def _build_next_action(self, *, queue_rows, issue_vouchers, alerts):
        ready_rows = [
            row
            for row in queue_rows
            if row.readiness_state
            in {
                PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
                PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
            }
            and row.local_stock_status in {'IN_STOCK', 'LOW_STOCK'}
        ]
        blocked_ready = [
            row
            for row in queue_rows
            if row.readiness_state
            in {
                PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
                PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
            }
            and row.local_stock_status in {'OUT_OF_STOCK', 'EXPIRED', 'UNMAPPED'}
        ]
        awaiting_payment = [
            row
            for row in queue_rows
            if row.readiness_state == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE
        ]
        pending_ack = [voucher for voucher in issue_vouchers if voucher['status'] in {'ISSUED', 'PARTIALLY_RECEIVED'}]

        if blocked_ready:
            return PharmacyDispensingNextActionResponse(
                severity='critical',
                title='Resolve stock blockers',
                detail=f"{len(blocked_ready)} ready prescriptions are blocked by local stock availability.",
            )
        if ready_rows:
            return PharmacyDispensingNextActionResponse(
                severity='warning' if any(row.aging_minutes >= self.DISPENSE_DELAY_THRESHOLD_MINUTES for row in ready_rows) else 'info',
                title='Ready to Dispense',
                detail=f"{len(ready_rows)} prescriptions can be dispensed now from local unit stock.",
            )
        if awaiting_payment:
            return PharmacyDispensingNextActionResponse(
                severity='warning',
                title='Awaiting Payment Clearance',
                detail=f"{len(awaiting_payment)} prescriptions are visible but blocked until payment or authorized exception.",
            )
        if pending_ack:
            return PharmacyDispensingNextActionResponse(
                severity='info',
                title='Acknowledge incoming stock',
                detail=f"{len(pending_ack)} issued vouchers are awaiting unit acknowledgement.",
            )
        if alerts:
            first = alerts[0]
            return PharmacyDispensingNextActionResponse(
                severity=first.severity,
                title=first.title,
                detail=first.detail,
            )
        return None

    def _build_alerts(self, *, queue_rows, local_stock_rows, issue_vouchers, generated_at: datetime):
        alerts: list[PharmacyDispensingAlertRowResponse] = []
        for row in queue_rows:
            if row.local_stock_status in {'OUT_OF_STOCK', 'EXPIRED', 'UNMAPPED'} and row.readiness_state in {
                PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
                PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
                PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE,
            }:
                alerts.append(
                    PharmacyDispensingAlertRowResponse(
                        id=f"prescription:{row.prescription_id}:stock",
                        severity='critical' if row.readiness_state == PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE else 'warning',
                        alert_type='STOCK_BLOCKER',
                        title=f"{row.item_name} is blocked in {row.assigned_unit_name or 'this unit'}",
                        detail='Local unit stock is not available for safe dispensing.',
                        patient_id=row.patient_id,
                        patient_name=row.patient_name,
                        patient_mrn=row.patient_mrn,
                        item_name=row.item_name,
                        occurred_at=row.issued_at,
                    )
                )
            elif row.readiness_state == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE and row.aging_minutes >= self.DISPENSE_DELAY_THRESHOLD_MINUTES:
                alerts.append(
                    PharmacyDispensingAlertRowResponse(
                        id=f"prescription:{row.prescription_id}:payment",
                        severity='warning',
                        alert_type='PAYMENT_DELAY',
                        title='Payment clearance is delaying dispense readiness',
                        detail=f"{row.patient_name or 'Patient'} has been waiting {row.aging_minutes} minutes for payment clearance.",
                        patient_id=row.patient_id,
                        patient_name=row.patient_name,
                        patient_mrn=row.patient_mrn,
                        item_name=row.item_name,
                        occurred_at=row.issued_at,
                    )
                )
            elif row.readiness_state in {
                PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
                PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
            } and row.aging_minutes >= self.DISPENSE_DELAY_THRESHOLD_MINUTES:
                alerts.append(
                    PharmacyDispensingAlertRowResponse(
                        id=f"prescription:{row.prescription_id}:aging",
                        severity='warning',
                        alert_type='DISPENSE_DELAY',
                        title='Ready prescription is aging',
                        detail=f"{row.patient_name or 'Patient'} has a ready prescription pending for {row.aging_minutes} minutes.",
                        patient_id=row.patient_id,
                        patient_name=row.patient_name,
                        patient_mrn=row.patient_mrn,
                        item_name=row.item_name,
                        occurred_at=row.issued_at,
                    )
                )
        for stock_row in local_stock_rows:
            if stock_row.stock_status in {'LOW_STOCK', 'EXPIRED'}:
                alerts.append(
                    PharmacyDispensingAlertRowResponse(
                        id=f"stock:{stock_row.inventory_item_id}:{stock_row.batch_number}",
                        severity='critical' if stock_row.stock_status == 'EXPIRED' else 'warning',
                        alert_type=stock_row.stock_status,
                        title=f"{stock_row.item_name} requires local stock attention",
                        detail=(
                            'Batch is expired and blocked from dispensing.'
                            if stock_row.stock_status == 'EXPIRED'
                            else f"Local stock is down to {stock_row.quantity_on_hand} units."
                        ),
                        item_name=stock_row.item_name,
                        occurred_at=generated_at,
                    )
                )
        for voucher in issue_vouchers:
            if voucher['status'] in {'ISSUED', 'PARTIALLY_RECEIVED'}:
                alerts.append(
                    PharmacyDispensingAlertRowResponse(
                        id=f"voucher:{voucher['id']}",
                        severity='info',
                        alert_type='RECEIVING_PENDING',
                        title='Incoming stock acknowledgement pending',
                        detail=f"Issue Voucher {voucher['voucher_number']} is waiting for unit acknowledgement.",
                        occurred_at=self._ensure_utc(voucher['issued_at']),
                    )
                )
        alerts.sort(key=lambda item: item.occurred_at, reverse=True)
        return alerts[: self.ALERT_LIMIT]

    def _build_activity_audit(self, *, clinic_id: UUID, unit_id: UUID, queue_rows, refill_requests, issue_vouchers, return_requests, reassignment_events, user_map):
        rows: list[PharmacyDispensingActivityRowResponse] = []
        queue_row_map = {str(row.prescription_id): row for row in queue_rows}
        dispense_events = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type.in_(
                    {'PHARMACY_PARTIAL_DISPENSED', 'PHARMACY_FULLY_DISPENSED'}
                ),
            )
            .order_by(EventLog.created_at.desc())
            .all()
        )
        unit_id_str = str(unit_id)
        for event in dispense_events:
            try:
                payload = json.loads(event.payload or '{}')
            except json.JSONDecodeError:
                continue
            if payload.get('dispensing_unit_id') != unit_id_str:
                continue
            queue_row = queue_row_map.get(payload.get('prescription_id'))
            if queue_row is None:
                continue
            remaining = payload.get('quantity_remaining')
            summary = (
                f"Partially dispensed {queue_row.item_name} to {queue_row.patient_name or 'patient'}"
                if event.event_type == 'PHARMACY_PARTIAL_DISPENSED'
                else f"Dispensed {queue_row.item_name} to {queue_row.patient_name or 'patient'}"
            )
            detail = (
                f"{payload.get('quantity_dispensed')} dispensed, {remaining} remaining."
                if event.event_type == 'PHARMACY_PARTIAL_DISPENSED'
                else f"Dispensed from local unit stock by {user_map.get(event.actor_id) or 'assigned pharmacist'}."
            )
            rows.append(
                PharmacyDispensingActivityRowResponse(
                    id=f"dispense-event:{event.id}",
                    occurred_at=self._ensure_utc(event.created_at),
                    action_type=event.event_type.replace('PHARMACY_', ''),
                    summary=summary,
                    detail=detail,
                    actor_name=user_map.get(event.actor_id),
                    patient_id=queue_row.patient_id,
                    patient_name=queue_row.patient_name,
                    patient_mrn=queue_row.patient_mrn,
                    item_name=queue_row.item_name,
                    severity='info',
                )
            )
        for request in refill_requests:
            rows.append(
                PharmacyDispensingActivityRowResponse(
                    id=f"refill:{request['id']}",
                    occurred_at=self._ensure_utc(request['requested_at']),
                    action_type='REFILL_REQUEST',
                    summary=f"Refill request submitted for {len(request['items'])} item(s)",
                    detail=f"Status: {request['status'].replace('_', ' ')}.",
                    actor_name=request.get('requested_by_name'),
                    severity='warning' if request['status'] in {'PENDING', 'APPROVED', 'BACKORDERED'} else 'info',
                )
            )
        for voucher in issue_vouchers:
            occurred_at = self._ensure_utc(voucher.get('acknowledged_at') or voucher['issued_at'])
            action_type = 'STOCK_RECEIVED' if voucher.get('acknowledged_at') else 'ISSUE_VOUCHER'
            rows.append(
                PharmacyDispensingActivityRowResponse(
                    id=f"voucher:{voucher['id']}",
                    occurred_at=occurred_at,
                    action_type=action_type,
                    summary=(
                        f"Acknowledged Issue Voucher {voucher['voucher_number']}"
                        if voucher.get('acknowledged_at')
                        else f"Incoming Issue Voucher {voucher['voucher_number']}"
                    ),
                    detail=f"{voucher['receiving_unit_name']} • Status: {voucher['status'].replace('_', ' ')}.",
                    actor_name=voucher.get('acknowledged_by_name') or voucher.get('issued_by_name'),
                    severity='warning' if voucher['status'] in {'ISSUED', 'PARTIALLY_RECEIVED'} else 'info',
                )
            )
        for return_request in return_requests:
            rows.append(
                PharmacyDispensingActivityRowResponse(
                    id=f"return:{return_request['id']}",
                    occurred_at=self._ensure_utc(
                        return_request.get('received_at')
                        or return_request.get('reviewed_at')
                        or return_request['requested_at']
                    ),
                    action_type='RETURN_TO_STORE',
                    summary=f"Return {return_request['return_number']} • {return_request['inventory_item_name']}",
                    detail=(
                        f"Status: {return_request['status'].replace('_', ' ')} • "
                        f"{return_request['quantity_now_returned']} requested."
                    ),
                    actor_name=(
                        return_request.get('received_by_name')
                        or return_request.get('reviewed_by_name')
                        or return_request.get('requested_by_name')
                    ),
                    item_name=return_request['inventory_item_name'],
                    severity='warning'
                    if return_request['status']
                    in {
                        'RETURN_PENDING_STORE_REVIEW',
                        'RETURN_ACCEPTED',
                    }
                    else 'info',
                )
            )
        for payload in reassignment_events.values():
            occurred_at = self._ensure_utc(payload['occurred_at'])
            rows.append(
                PharmacyDispensingActivityRowResponse(
                    id=f"reassign:{payload['event_id']}",
                    occurred_at=occurred_at,
                    action_type='REASSIGNED',
                    summary='Prescription reassigned into this dispensing unit',
                    detail=payload.get('reason') or 'Reassignment recorded.',
                    actor_name=user_map.get(payload.get('actor_id')), 
                    severity='info',
                )
            )
        rows.sort(key=lambda item: item.occurred_at, reverse=True)
        return rows[: self.ACTIVITY_LIMIT]

    def _build_queue_row(
        self,
        *,
        prescription: Prescription,
        visit: Visit | None,
        patient: dict | None,
        patient_mrn: str | None,
        source_unit: ServiceLine | None,
        inventory_item: PharmacyInventoryItem | None,
        lots: list[PharmacyUnitStockLot],
        billing_item: BillingItem | None,
        assigned_unit_name: str,
        cashier_pay_point_name: str | None,
        user_map: dict[UUID, str | None],
        generated_at: datetime,
        reassignment_event: dict | None,
    ) -> PharmacyDispensingQueueRowResponse:
        available_quantity = sum(lot.quantity_on_hand for lot in lots if not self._lot_is_expired(lot.expiry_date))
        priority = self._resolve_priority(visit=visit, prescription=prescription)
        return PharmacyDispensingQueueRowResponse(
            prescription_id=prescription.id,
            visit_id=prescription.visit_id,
            patient_id=visit.patient_id if visit else None,
            patient_name=patient['full_name'] if patient else None,
            patient_mrn=patient_mrn,
            source_department_name=source_unit.name if source_unit else (visit.service_line.value if visit else None),
            item_name=prescription.drug_name,
            dosage=prescription.dosage,
            frequency=prescription.frequency,
            duration=prescription.duration,
            instructions=prescription.instructions,
            quantity_prescribed=prescription.quantity_prescribed,
            quantity_dispensed_total=prescription.quantity_dispensed_total,
            quantity_remaining=prescription.quantity_remaining,
            readiness_state=prescription.workflow_status,
            payment_state=self._resolve_payment_state(prescription=prescription, billing_item=billing_item),
            assigned_unit_id=prescription.assigned_dispensing_unit_id,
            assigned_unit_name=assigned_unit_name,
            cashier_pay_point_name=cashier_pay_point_name,
            priority=priority,
            aging_minutes=max(0, int((generated_at - self._ensure_utc(prescription.issued_at)).total_seconds() // 60)),
            exception_authorization_type=prescription.exception_authorization_type,
            local_stock_status=self._stock_status_for_lots(
                inventory_item=inventory_item,
                lots=lots,
                available_quantity=available_quantity,
            ),
            local_stock_available_quantity=available_quantity,
            prescribed_by_name=user_map.get(prescription.prescribed_by),
            dispensed_by_name=user_map.get(prescription.dispensed_by) if prescription.dispensed_by else None,
            issued_at=self._ensure_utc(prescription.issued_at),
            dispensed_at=self._ensure_utc(prescription.dispensed_at) if prescription.dispensed_at else None,
            recently_reassigned=bool(reassignment_event),
            last_reassignment_at=self._ensure_utc(reassignment_event['occurred_at']) if reassignment_event else None,
            reassignment_reason=reassignment_event.get('reason') if reassignment_event else None,
            reassignment_note=reassignment_event.get('note') if reassignment_event else None,
        )

    def _load_prescriptions(self, *, clinic_id: UUID, unit_id: UUID) -> list[Prescription]:
        return (
            self.db.query(Prescription)
            .join(Visit, Prescription.visit_id == Visit.id)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.status != VisitStatus.CANCELLED,
                Prescription.assigned_dispensing_unit_id == unit_id,
            )
            .order_by(Prescription.issued_at.desc())
            .all()
        )

    def _load_visits(self, visit_ids: set[UUID]) -> dict[UUID, Visit]:
        if not visit_ids:
            return {}
        rows = self.db.query(Visit).filter(Visit.id.in_(visit_ids)).all()
        return {row.id: row for row in rows}

    def _load_patients(self, *, visits: dict[UUID, Visit]) -> dict[UUID, dict]:
        patient_ids = {visit.patient_id for visit in visits.values()}
        if not patient_ids:
            return {}
        patients = self.db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
        mrn_rows = (
            self.db.query(PatientMRN.patient_id, PatientMRN.mrn)
            .filter(PatientMRN.patient_id.in_(patient_ids), PatientMRN.status == MRNStatus.ACTIVE)
            .all()
        )
        mrn_map = {patient_id: mrn for patient_id, mrn in mrn_rows}
        return {
            patient.id: {
                'full_name': patient.full_name,
                'mrn': mrn_map.get(patient.id),
            }
            for patient in patients
        }

    def _load_user_map(self, user_ids: set[UUID]) -> dict[UUID, str | None]:
        if not user_ids:
            return {}
        users = self.db.query(User).filter(User.id.in_(user_ids)).all()
        return {user.id: user.full_name for user in users}

    def _load_service_line_map(self, unit_ids: set[UUID | None]) -> dict[UUID, ServiceLine]:
        normalized_ids = [unit_id for unit_id in unit_ids if unit_id is not None]
        if not normalized_ids:
            return {}
        rows = self.db.query(ServiceLine).filter(ServiceLine.id.in_(normalized_ids)).all()
        return {row.id: row for row in rows}

    def _load_billing_map(self, billing_item_ids: set[UUID]) -> dict[UUID, BillingItem]:
        if not billing_item_ids:
            return {}
        rows = self.db.query(BillingItem).filter(BillingItem.id.in_(billing_item_ids)).all()
        return {row.id: row for row in rows}

    def _load_pay_point_map(self, pay_point_ids: set[UUID]) -> dict[UUID, str]:
        if not pay_point_ids:
            return {}
        rows = self.db.query(CashierPayPoint).filter(CashierPayPoint.id.in_(pay_point_ids)).all()
        return {row.id: row.name for row in rows}

    def _inventory_lookup_key(self, prescription: Prescription) -> str:
        if prescription.pharmacy_catalog_item_id is not None:
            return f"catalog:{prescription.pharmacy_catalog_item_id}"
        return f"name:{(prescription.drug_name or '').strip().lower()}"

    def _load_inventory_map(self, *, clinic_id: UUID, prescriptions: list[Prescription]) -> dict[str, PharmacyInventoryItem]:
        catalog_item_ids = {
            prescription.pharmacy_catalog_item_id
            for prescription in prescriptions
            if prescription.pharmacy_catalog_item_id is not None
        }
        normalized_names = {
            (prescription.drug_name or '').strip().lower()
            for prescription in prescriptions
            if (prescription.drug_name or '').strip()
        }
        if not catalog_item_ids and not normalized_names:
            return {}
        rows = (
            self.db.query(PharmacyInventoryItem)
            .filter(PharmacyInventoryItem.clinic_id == clinic_id, PharmacyInventoryItem.lifecycle_status == 'ACTIVE')
            .all()
        )
        inventory_map: dict[str, PharmacyInventoryItem] = {}
        for row in rows:
            if row.catalog_item_id is not None and row.catalog_item_id in catalog_item_ids:
                inventory_map[f"catalog:{row.catalog_item_id}"] = row
            key = (row.generic_name or '').strip().lower()
            name_key = f"name:{key}"
            if key in normalized_names and name_key not in inventory_map:
                inventory_map[name_key] = row
        return inventory_map

    def _load_local_stock(self, *, clinic_id: UUID, unit_id: UUID, prescriptions: list[Prescription]):
        inventory_map = self._load_inventory_map(clinic_id=clinic_id, prescriptions=prescriptions)
        lots = (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.clinic_id == clinic_id,
                PharmacyUnitStockLot.service_line_id == unit_id,
            )
            .order_by(PharmacyUnitStockLot.expiry_date.asc().nulls_last(), PharmacyUnitStockLot.batch_number.asc())
            .all()
        )
        inventory_ids = {lot.inventory_item_id for lot in lots} | {item.id for item in inventory_map.values()}
        inventory_rows = (
            self.db.query(PharmacyInventoryItem)
            .filter(PharmacyInventoryItem.id.in_(inventory_ids))
            .all()
            if inventory_ids
            else []
        )
        inventory_by_id = {item.id: item for item in inventory_rows}
        lots_by_inventory_id: dict[UUID, list[PharmacyUnitStockLot]] = defaultdict(list)
        for lot in lots:
            lots_by_inventory_id[lot.inventory_item_id].append(lot)

        local_stock_rows: list[PharmacyDispensingLocalStockRowResponse] = []
        for inventory_item_id, item_lots in lots_by_inventory_id.items():
            inventory_item = inventory_by_id.get(inventory_item_id)
            if inventory_item is None:
                continue
            for lot in item_lots:
                expired = self._lot_is_expired(lot.expiry_date)
                if expired:
                    stock_status = 'EXPIRED'
                elif lot.quantity_on_hand <= inventory_item.low_stock_threshold:
                    stock_status = 'LOW_STOCK'
                else:
                    stock_status = 'IN_STOCK'
                local_stock_rows.append(
                    PharmacyDispensingLocalStockRowResponse(
                        inventory_item_id=inventory_item.id,
                        item_name=inventory_item.generic_name,
                        batch_number=lot.batch_number,
                        expiry_date=lot.expiry_date,
                        quantity_on_hand=lot.quantity_on_hand,
                        low_stock_threshold=inventory_item.low_stock_threshold,
                        stock_status=stock_status,
                        blocked=expired,
                    )
                )
        return inventory_map, lots_by_inventory_id, local_stock_rows

    def _list_lots_for_inventory_item(
        self,
        *,
        clinic_id: UUID,
        unit_id: UUID,
        inventory_item_id: UUID | None,
    ) -> list[PharmacyUnitStockLot]:
        if inventory_item_id is None:
            return []
        return (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.clinic_id == clinic_id,
                PharmacyUnitStockLot.service_line_id == unit_id,
                PharmacyUnitStockLot.inventory_item_id == inventory_item_id,
            )
            .order_by(PharmacyUnitStockLot.expiry_date.asc().nulls_last(), PharmacyUnitStockLot.created_at.asc())
            .all()
        )

    def _load_reassignment_events(self, *, clinic_id: UUID, unit_id: UUID) -> dict[str, dict]:
        rows = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type == 'PHARMACY_REASSIGNED',
            )
            .all()
        )
        latest: dict[str, dict] = {}
        target_unit_id = str(unit_id)
        for row in rows:
            try:
                payload = json.loads(row.payload or '{}')
            except json.JSONDecodeError:
                continue
            if payload.get('target_unit_id') != target_unit_id:
                continue
            prescription_id = payload.get('prescription_id')
            if not prescription_id:
                continue
            previous = latest.get(prescription_id)
            occurred_at = self._ensure_utc(getattr(row, 'created_at', None))
            if previous and self._ensure_utc(previous['occurred_at']) >= occurred_at:
                continue
            latest[prescription_id] = {
                'event_id': str(row.id),
                'actor_id': row.actor_id,
                'occurred_at': occurred_at,
                'reason': payload.get('reason'),
                'note': payload.get('note'),
            }
        return latest

    def _list_reassignment_targets(self, *, clinic_id: UUID, current_unit_id: UUID):
        rows = (
            self.db.query(ServiceLine)
            .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.is_active == True,
                ServiceLine.id != current_unit_id,
                PharmacyUnitProfile.unit_category != PharmacyUnitCategory.STORE,
            )
            .order_by(ServiceLine.name.asc())
            .all()
        )
        return [
            PharmacyDispensingReassignmentTargetResponse(unit_id=row.id, unit_name=row.name)
            for row in rows
        ]

    def _resolve_priority(self, *, visit: Visit | None, prescription: Prescription) -> str:
        if prescription.exception_authorization_type == PharmacyExceptionAuthorizationType.EMERGENCY_OVERRIDE:
            return 'EMERGENCY'
        if visit and visit.triage_acuity == ClinicalPriorityLevel.CRITICAL:
            return 'EMERGENCY'
        if visit and visit.triage_acuity == ClinicalPriorityLevel.URGENT:
            return 'URGENT'
        return 'ROUTINE'

    def _resolve_payment_state(self, *, prescription: Prescription, billing_item: BillingItem | None) -> str:
        if billing_item and billing_item.status == BillingItemStatus.PAID:
            return 'PAID'
        if prescription.exception_authorization_type != PharmacyExceptionAuthorizationType.NONE:
            return 'EXCEPTION_AUTHORIZED'
        return 'AWAITING_PAYMENT_CLEARANCE'

    def _stock_status_for_lots(self, *, inventory_item: PharmacyInventoryItem | None, lots: list[PharmacyUnitStockLot], available_quantity: int) -> str:
        if inventory_item is None:
            return 'UNMAPPED'
        has_expired_stock = any(
            lot.quantity_on_hand > 0 and self._lot_is_expired(lot.expiry_date)
            for lot in lots
        )
        if available_quantity <= 0:
            return 'EXPIRED' if has_expired_stock else 'OUT_OF_STOCK'
        if available_quantity <= inventory_item.low_stock_threshold:
            return 'LOW_STOCK'
        return 'IN_STOCK'

    def _lot_is_expired(self, expiry_date: date | None) -> bool:
        return bool(expiry_date and expiry_date < datetime.now(timezone.utc).date())

    def _is_same_day(self, value: datetime, reference: datetime) -> bool:
        return self._ensure_utc(value).date() == self._ensure_utc(reference).date()

    def _ensure_utc(self, value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
