from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from statistics import mean
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.billing_item import BillingItem
from app.models.cashier_pay_point import CashierPayPoint
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.payment_receipt import PaymentReceipt
from app.models.payment_receipt_item import PaymentReceiptItem
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_stock_movement import PharmacyStockMovement
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.pharmacy_user_unit_access import PharmacyUserUnitAccess
from app.models.prescription import Prescription
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.pharmacy_hod import (
    PharmacyHodActivityAuditRowResponse,
    PharmacyHodBottleneckItemResponse,
    PharmacyHodCriticalAlertRowResponse,
    PharmacyHodDashboardResponse,
    PharmacyHodDispensingOversightRowResponse,
    PharmacyHodExceptionOversightRowResponse,
    PharmacyHodIssueVoucherRowResponse,
    PharmacyHodOverviewMetricResponse,
    PharmacyHodPayPointPerformanceResponse,
    PharmacyHodReceiptRegisterRowResponse,
    PharmacyHodRefillRequestRowResponse,
    PharmacyHodReportsAnalyticsResponse,
    PharmacyHodSalesRevenueByUnitResponse,
    PharmacyHodSalesRevenueResponse,
    PharmacyHodSalesRevenueRowResponse,
    PharmacyHodStaffPerformanceResponse,
    PharmacyHodStaffSummaryResponse,
    PharmacyHodStockRiskRowResponse,
    PharmacyHodSystemHealthResponse,
    PharmacyHodUnitAssignmentMemberResponse,
    PharmacyHodUnitAssignmentResponse,
    PharmacyHodUnitContextResponse,
    PharmacyHodUnitOperationResponse,
    PharmacyHodUnitSummaryResponse,
)
from app.services.event_service import EventService
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.shared.enums import (
    BillingItemStatus,
    MRNStatus,
    PharmacyExceptionAuthorizationType,
    PharmacyIssueVoucherStatus,
    PharmacyPrescriptionWorkflowStatus,
    PharmacyRefillRequestStatus,
    PharmacyUnitCategory,
    PrescriptionFulfillmentType,
    PrescriptionStatus,
    UserRole,
)


TERMINAL_PRESCRIPTION_STATUSES = {
    PharmacyPrescriptionWorkflowStatus.DISPENSED,
    PharmacyPrescriptionWorkflowStatus.CANCELLED,
    PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED,
}

OPEN_QUEUE_STATUSES = {
    PharmacyPrescriptionWorkflowStatus.ASSIGNED,
    PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE,
    PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
    PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
    PharmacyPrescriptionWorkflowStatus.IN_DISPENSE,
    PharmacyPrescriptionWorkflowStatus.REASSIGNED,
}

ACTIONABLE_READY_STATUSES = {
    PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
    PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
}

PHARMACY_EVENT_TYPES = {
    "PHARMACY_REFILL_REQUESTED",
    "PHARMACY_CATALOG_REQUEST_SUBMITTED",
    "PHARMACY_CATALOG_CMD_APPROVED",
    "PHARMACY_CATALOG_CMD_REJECTED",
    "PHARMACY_CATALOG_PRICED",
    "PHARMACY_CATALOG_ACTIVATED",
    "PHARMACY_CATALOG_DEACTIVATED",
    "PHARMACY_CMD_APPROVED",
    "PHARMACY_CMD_REJECTED",
    "PHARMACY_ISSUE_VOUCHER_GENERATED",
    "PHARMACY_ISSUE_DISPATCHED",
    "PHARMACY_ACKNOWLEDGEMENT_RECORDED",
    "PHARMACY_REASSIGNED",
    "PHARMACY_PARTIAL_DISPENSED",
    "PHARMACY_FULLY_DISPENSED",
    "PHARMACY_STAFF_ASSIGNMENT_UPDATED",
}


@dataclass
class PharmacyUnitRecord:
    id: UUID
    name: str
    category: PharmacyUnitCategory


class PharmacyHodDashboardService:
    DISPENSE_DELAY_THRESHOLD_MINUTES = 20
    EXPIRY_SOON_DAYS = 45
    HIGH_PENDING_THRESHOLD = 5
    MAX_ACTIVITY_ROWS = 40

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PharmacyHodDashboardResponse:
        start_date, end_date, start_dt, end_dt = self._normalize_date_range(
            start_date=start_date,
            end_date=end_date,
        )
        generated_at = datetime.now(timezone.utc)

        units = self._list_pharmacy_units(clinic_id=clinic_id)
        unit_map = {unit.id: unit for unit in units}
        user_map = self._load_user_map(clinic_id=clinic_id)
        prescription_rows = self._load_prescription_rows(
            clinic_id=clinic_id,
            unit_map=unit_map,
            user_map=user_map,
            generated_at=generated_at,
        )
        staff_control = self._build_staff_control(
            clinic_id=clinic_id,
            units=units,
            user_map=user_map,
        )
        staff_by_user_id = {row.user_id: row for row in staff_control}
        unit_assignment = self._build_unit_assignment(units=units, staff_control=staff_control)

        store_supply = self._build_store_supply_rows(clinic_id=clinic_id)
        configuration_requests = PharmacyCatalogGovernanceService(self.db).list_catalog_items(
            clinic_id=clinic_id,
        )
        issue_vouchers = self._build_issue_voucher_rows(clinic_id=clinic_id, units=units)
        stock_risk_rows = self._build_stock_risk_rows(clinic_id=clinic_id, units=units)
        sales_revenue, receipt_register = self._build_finance_rows(
            clinic_id=clinic_id,
            prescription_rows=prescription_rows,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        pay_point_performance = self._build_pay_point_performance(
            clinic_id=clinic_id,
            sales_rows=sales_revenue.rows,
            prescription_rows=prescription_rows,
            currency=sales_revenue.currency,
        )
        exception_rows = self._build_exception_rows(
            prescription_rows=prescription_rows,
            user_map=user_map,
        )
        critical_alerts = self._build_critical_alerts(
            prescription_rows=prescription_rows,
            store_supply=store_supply,
            stock_risk_rows=stock_risk_rows,
            generated_at=generated_at,
        )
        unit_summary = self._build_unit_summary(
            units=units,
            prescription_rows=prescription_rows,
            sales_rows=sales_revenue.rows,
            stock_risk_rows=stock_risk_rows,
        )
        unit_operations = self._build_unit_operations(
            units=units,
            prescription_rows=prescription_rows,
            stock_risk_rows=stock_risk_rows,
            staff_control=staff_control,
        )
        bottlenecks = self._build_bottlenecks(
            unit_operations=unit_operations,
            stock_risk_rows=stock_risk_rows,
            critical_alerts=critical_alerts,
        )
        activity_audit = self._build_activity_audit(
            clinic_id=clinic_id,
            unit_map=unit_map,
            user_map=user_map,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        staff_performance = self._build_staff_performance(
            clinic_id=clinic_id,
            start_dt=start_dt,
            end_dt=end_dt,
            staff_control=staff_control,
            prescription_rows=prescription_rows,
            user_map=user_map,
        )
        system_health = self._build_system_health(
            prescription_rows=prescription_rows,
            critical_alerts=critical_alerts,
            start_dt=start_dt,
            end_dt=end_dt,
            clinic_id=clinic_id,
        )

        pending_refill_requests = sum(
            1
            for item in store_supply
            if item.status == PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL
        )
        awaiting_payment = sum(
            1
            for row in prescription_rows
            if row["workflow_status"] == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE
        )
        ready_to_dispense = sum(
            1
            for row in prescription_rows
            if row["workflow_status"] in ACTIONABLE_READY_STATUSES
        )
        delayed_dispense_count = sum(1 for row in prescription_rows if row["delay_minutes"] >= self.DISPENSE_DELAY_THRESHOLD_MINUTES and row["workflow_status"] in OPEN_QUEUE_STATUSES)
        pending_prescriptions = sum(
            1 for row in prescription_rows if row["workflow_status"] in OPEN_QUEUE_STATUSES
        )

        overview = PharmacyHodOverviewMetricResponse(
            pending_prescriptions=pending_prescriptions,
            ready_to_dispense=ready_to_dispense,
            awaiting_payment_clearance=awaiting_payment,
            stock_risk_items=len(stock_risk_rows),
            pending_refill_requests=pending_refill_requests,
            critical_alerts=len(critical_alerts),
            delayed_dispense_count=delayed_dispense_count,
            currency=sales_revenue.currency,
            last_updated_at=generated_at,
        )

        reports_analytics = PharmacyHodReportsAnalyticsResponse(
            revenue_by_unit=sales_revenue.revenue_by_unit,
            revenue_by_pay_point=pay_point_performance,
            refill_frequency_by_unit=self._build_refill_frequency(store_supply=store_supply),
            dispense_turnaround_by_unit=self._build_turnaround_analytics(unit_operations=unit_operations),
            stock_risk_counts=self._build_stock_risk_counts(stock_risk_rows=stock_risk_rows),
        )

        return PharmacyHodDashboardResponse(
            generated_at=generated_at,
            start_date=start_date,
            end_date=end_date,
            overview=overview,
            system_health=system_health,
            unit_summary=unit_summary,
            pay_point_performance=pay_point_performance,
            bottlenecks=bottlenecks,
            unit_operations=unit_operations,
            dispensing_oversight=self._build_dispensing_oversight(
                prescription_rows=prescription_rows,
                staff_by_user_id=staff_by_user_id,
            ),
            store_supply=store_supply,
            issue_vouchers=issue_vouchers,
            staff_control=staff_control,
            unit_assignment=unit_assignment,
            pending_approvals=[
                row
                for row in store_supply
                if row.status == PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL
            ],
            exception_oversight=exception_rows,
            critical_alerts=critical_alerts,
            stock_risk_expiry=stock_risk_rows,
            activity_audit=activity_audit,
            staff_performance=staff_performance,
            sales_revenue=sales_revenue,
            receipt_register=receipt_register,
            reports_analytics=reports_analytics,
            configuration_requests=configuration_requests,
            configuration_requests_enabled=True,
        )

    def snapshot_signature(self, snapshot: PharmacyHodDashboardResponse) -> str:
        payload = snapshot.model_dump(mode="json")
        payload["generated_at"] = None
        payload["overview"]["last_updated_at"] = None
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def update_staff_assignment(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        staff_id: UUID,
        payload,
    ) -> PharmacyHodStaffSummaryResponse:
        target_user = (
            self.db.query(User)
            .filter(User.clinic_id == clinic_id, User.id == staff_id)
            .first()
        )
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pharmacy staff member not found",
            )

        try:
            target_role = UserRole(target_user.role)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Target account role is not supported for pharmacy governance",
            ) from exc

        if target_role not in {
            UserRole.PHARMACY,
            UserRole.PHARMACY_HOD,
            UserRole.PHARMACY_STORE_OFFICER,
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Only pharmacy department accounts can be governed from this dashboard",
            )

        if target_role in {
            UserRole.PHARMACY_HOD,
            UserRole.PHARMACY_STORE_OFFICER,
        } and payload.allowed_unit_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Pharmacy HOD and store accounts do not use operational dispensing-unit assignments",
            )

        PharmacyUnitAccessService(self.db).sync_user_units(
            clinic_id=clinic_id,
            user=target_user,
            role=target_role,
            allowed_unit_ids=list(payload.allowed_unit_ids),
            default_unit_id=payload.default_unit_id,
        )

        EventService(self.db).build_event(
            event_type="PHARMACY_STAFF_ASSIGNMENT_UPDATED",
            actor_id=actor.id,
            actor_role=getattr(actor.role, "value", actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "target_user_id": str(target_user.id),
                "target_user_name": target_user.full_name,
                "allowed_unit_ids": [str(unit_id) for unit_id in payload.allowed_unit_ids],
                "default_unit_id": str(payload.default_unit_id) if payload.default_unit_id else None,
            },
        )
        self.db.commit()

        staff_rows = self._build_staff_control(
            clinic_id=clinic_id,
            units=self._list_pharmacy_units(clinic_id=clinic_id),
            user_map=self._load_user_map(clinic_id=clinic_id),
        )
        for row in staff_rows:
            if row.user_id == target_user.id:
                return row
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Updated pharmacy staff assignment could not be reloaded",
        )

    def _normalize_date_range(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date, datetime, datetime]:
        today = datetime.now(timezone.utc).date()
        resolved_end = end_date or today
        resolved_start = start_date or resolved_end
        if resolved_start > resolved_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Start date must not be after end date",
            )
        start_dt = datetime.combine(resolved_start, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(resolved_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
        return resolved_start, resolved_end, start_dt, end_dt

    def _ensure_utc(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _list_pharmacy_units(self, *, clinic_id: UUID) -> list[PharmacyUnitRecord]:
        rows = (
            self.db.query(ServiceLine, PharmacyUnitProfile)
            .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
            .filter(ServiceLine.clinic_id == clinic_id, ServiceLine.is_active == True)
            .order_by(ServiceLine.name.asc())
            .all()
        )
        return [
            PharmacyUnitRecord(id=unit.id, name=unit.name, category=profile.unit_category)
            for unit, profile in rows
        ]

    def _load_user_map(self, *, clinic_id: UUID) -> dict[UUID, User]:
        users = self.db.query(User).filter(User.clinic_id == clinic_id).all()
        return {user.id: user for user in users}

    def _load_patient_context(self, *, clinic_id: UUID, visit_ids: Iterable[UUID]) -> dict[UUID, dict]:
        unique_visit_ids = list({visit_id for visit_id in visit_ids})
        if not unique_visit_ids:
            return {}
        visits = self.db.query(Visit).filter(Visit.id.in_(unique_visit_ids)).all()
        patient_ids = {visit.patient_id for visit in visits}
        patients = self.db.query(Patient).filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
        mrn_rows = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id.in_(patient_ids),
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .all()
            if patient_ids
            else []
        )
        patient_map = {patient.id: patient for patient in patients}
        mrn_map = {row.patient_id: row.mrn for row in mrn_rows}
        payload: dict[UUID, dict] = {}
        for visit in visits:
            patient = patient_map.get(visit.patient_id)
            payload[visit.id] = {
                "visit": visit,
                "patient_id": visit.patient_id,
                "patient_name": patient.full_name if patient else None,
                "patient_mrn": mrn_map.get(visit.patient_id),
            }
        return payload

    def _load_prescription_rows(
        self,
        *,
        clinic_id: UUID,
        unit_map: dict[UUID, PharmacyUnitRecord],
        user_map: dict[UUID, User],
        generated_at: datetime,
    ) -> list[dict]:
        prescriptions = (
            self.db.query(Prescription)
            .filter(Prescription.clinic_id == clinic_id)
            .order_by(Prescription.issued_at.desc())
            .all()
        )
        billing_item_ids = {
            row.billing_item_id for row in prescriptions if row.billing_item_id is not None
        }
        billing_items = (
            self.db.query(BillingItem)
            .filter(BillingItem.id.in_(billing_item_ids))
            .all()
            if billing_item_ids
            else []
        )
        billing_item_map = {item.id: item for item in billing_items}
        patient_context = self._load_patient_context(
            clinic_id=clinic_id,
            visit_ids=[row.visit_id for row in prescriptions],
        )
        results: list[dict] = []
        for prescription in prescriptions:
            unit = unit_map.get(prescription.assigned_dispensing_unit_id)
            billing_item = billing_item_map.get(prescription.billing_item_id)
            patient_ctx = patient_context.get(prescription.visit_id, {})
            issued_at = self._ensure_utc(prescription.issued_at)
            resolved_at = (
                self._ensure_utc(prescription.dispensed_at)
                or self._ensure_utc(prescription.cancelled_at)
                or self._ensure_utc(prescription.externally_fulfilled_at)
            )
            effective_end = resolved_at or generated_at
            delay_minutes = max(
                0,
                int((effective_end - issued_at).total_seconds() // 60),
            )
            results.append(
                {
                    "prescription_id": prescription.id,
                    "visit_id": prescription.visit_id,
                    "patient_id": patient_ctx.get("patient_id"),
                    "patient_name": patient_ctx.get("patient_name"),
                    "patient_mrn": patient_ctx.get("patient_mrn"),
                    "item_name": prescription.drug_name,
                    "billing_item_id": prescription.billing_item_id,
                    "unit_id": prescription.assigned_dispensing_unit_id,
                    "unit_name": unit.name if unit else None,
                    "unit_category": unit.category if unit else None,
                    "workflow_status": prescription.workflow_status,
                    "status": prescription.status,
                    "billing_status": billing_item.status.value if billing_item else "UNLINKED",
                    "payment_state": billing_item.status.value if billing_item else "UNLINKED",
                    "assigned_staff_id": prescription.dispensed_by,
                    "assigned_staff_name": user_map.get(prescription.dispensed_by).full_name if prescription.dispensed_by in user_map else None,
                    "delay_minutes": delay_minutes,
                    "exception_authorization_type": prescription.exception_authorization_type,
                    "authorized_by_id": prescription.exception_authorized_by,
                    "authorized_by_name": user_map.get(prescription.exception_authorized_by).full_name if prescription.exception_authorized_by in user_map else None,
                    "authorized_at": self._ensure_utc(prescription.exception_authorized_at),
                    "issued_at": issued_at,
                    "resolved_at": resolved_at,
                    "assigned_cashier_pay_point_id": prescription.assigned_cashier_pay_point_id,
                }
            )
        return results

    def _build_dispensing_oversight(
        self,
        *,
        prescription_rows: list[dict],
        staff_by_user_id: dict[UUID, PharmacyHodStaffSummaryResponse],
    ) -> list[PharmacyHodDispensingOversightRowResponse]:
        return [
            PharmacyHodDispensingOversightRowResponse(
                prescription_id=row["prescription_id"],
                visit_id=row["visit_id"],
                patient_id=row["patient_id"],
                patient_name=row["patient_name"],
                patient_mrn=row["patient_mrn"],
                unit_id=row["unit_id"],
                unit_name=row["unit_name"],
                item_name=row["item_name"],
                readiness_state=row["workflow_status"],
                payment_state=row["payment_state"],
                assigned_staff_id=row["assigned_staff_id"],
                assigned_staff_name=(
                    staff_by_user_id[row["assigned_staff_id"]].full_name
                    if row["assigned_staff_id"] in staff_by_user_id
                    else row["assigned_staff_name"]
                ),
                delay_minutes=row["delay_minutes"],
                exception_authorization_type=row["exception_authorization_type"],
                issued_at=row["issued_at"],
                resolved_at=row["resolved_at"],
            )
            for row in prescription_rows[:120]
        ]

    def _build_store_supply_rows(self, *, clinic_id: UUID) -> list[PharmacyHodRefillRequestRowResponse]:
        raw_rows = PharmacySupplyService(self.db).list_hod_refill_requests(clinic_id=clinic_id)
        response: list[PharmacyHodRefillRequestRowResponse] = []
        for row in raw_rows:
            items = row.get("items", [])
            response.append(
                PharmacyHodRefillRequestRowResponse(
                    request_id=row["id"],
                    requesting_unit_id=row["requesting_unit_id"],
                    requesting_unit_name=row["requesting_unit_name"],
                    requested_by_id=row["requested_by"],
                    requested_by_name=row.get("requested_by_name"),
                    status=row["status"],
                    urgency=row.get("urgency"),
                    requested_at=self._ensure_utc(row["requested_at"]),
                    item_count=len(items),
                    total_requested_quantity=sum(item["requested_quantity"] for item in items),
                    total_approved_quantity=sum((item["approved_quantity"] or 0) for item in items),
                )
            )
        return response

    def _build_issue_voucher_rows(
        self,
        *,
        clinic_id: UUID,
        units: list[PharmacyUnitRecord],
    ) -> list[PharmacyHodIssueVoucherRowResponse]:
        vouchers: list[PharmacyHodIssueVoucherRowResponse] = []
        store_units = [unit for unit in units if unit.category == PharmacyUnitCategory.STORE]
        service = PharmacySupplyService(self.db)
        for store_unit in store_units:
            for row in service.list_store_issue_vouchers(
                clinic_id=clinic_id,
                store_unit_id=store_unit.id,
            ):
                items = row.get("items", [])
                partial_issue = any(item["received_quantity"] < item["issued_quantity"] for item in items)
                backorder_pending = row["status"] in {
                    PharmacyIssueVoucherStatus.ISSUED,
                    PharmacyIssueVoucherStatus.PARTIALLY_RECEIVED,
                }
                vouchers.append(
                    PharmacyHodIssueVoucherRowResponse(
                        voucher_id=row["id"],
                        voucher_number=row["voucher_number"],
                        store_unit_id=row["store_unit_id"],
                        store_unit_name=row["store_unit_name"],
                        receiving_unit_id=row["receiving_unit_id"],
                        receiving_unit_name=row["receiving_unit_name"],
                        status=row["status"],
                        approved_by_name=row.get("approved_by_name"),
                        issued_by_name=row.get("issued_by_name"),
                        acknowledged_by_name=row.get("acknowledged_by_name"),
                        issued_at=self._ensure_utc(row["issued_at"]),
                        acknowledged_at=self._ensure_utc(row.get("acknowledged_at")),
                        partial_issue=partial_issue,
                        backorder_pending=backorder_pending,
                        item_count=len(items),
                    )
                )
        vouchers.sort(key=lambda row: row.issued_at, reverse=True)
        return vouchers[:80]

    def _build_staff_control(
        self,
        *,
        clinic_id: UUID,
        units: list[PharmacyUnitRecord],
        user_map: dict[UUID, User],
    ) -> list[PharmacyHodStaffSummaryResponse]:
        pharmacy_users = [
            user
            for user in user_map.values()
            if user.role in {
                UserRole.PHARMACY.value,
                UserRole.PHARMACY_HOD.value,
                UserRole.PHARMACY_STORE_OFFICER.value,
            }
        ]
        unit_lookup = {unit.id: unit for unit in units if unit.category != PharmacyUnitCategory.STORE}
        access_rows = (
            self.db.query(PharmacyUserUnitAccess)
            .filter(PharmacyUserUnitAccess.clinic_id == clinic_id)
            .all()
        )
        access_by_user: dict[UUID, list[PharmacyUserUnitAccess]] = defaultdict(list)
        for row in access_rows:
            access_by_user[row.user_id].append(row)

        latest_events = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type.in_(PHARMACY_EVENT_TYPES),
            )
            .order_by(EventLog.created_at.desc())
            .all()
        )
        recent_by_actor: dict[UUID, EventLog] = {}
        for event in latest_events:
            if event.actor_id and event.actor_id not in recent_by_actor:
                recent_by_actor[event.actor_id] = event

        summaries: list[PharmacyHodStaffSummaryResponse] = []
        for user in sorted(pharmacy_users, key=lambda item: (item.full_name or item.email).lower()):
            try:
                role = UserRole(user.role)
            except ValueError:
                continue
            accesses = access_by_user.get(user.id, [])
            assigned_units = [
                PharmacyHodUnitContextResponse(
                    id=row.service_line_id,
                    name=unit_lookup[row.service_line_id].name,
                    category=unit_lookup[row.service_line_id].category,
                )
                for row in sorted(accesses, key=lambda item: (not item.is_default, str(item.service_line_id)))
                if row.is_active and row.service_line_id in unit_lookup
            ]
            default_row = next((row for row in accesses if row.is_default and row.is_active), None)
            default_unit = unit_lookup.get(default_row.service_line_id) if default_row else None
            recent_event = recent_by_actor.get(user.id)
            summaries.append(
                PharmacyHodStaffSummaryResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    role=role,
                    is_active=bool(user.is_active),
                    assigned_units=assigned_units,
                    default_unit_id=default_unit.id if default_unit else None,
                    default_unit_name=default_unit.name if default_unit else None,
                    recent_activity_summary=self._event_summary(recent_event) if recent_event else None,
                    recent_activity_at=self._ensure_utc(recent_event.created_at) if recent_event else None,
                )
            )
        return summaries

    def _build_unit_assignment(
        self,
        *,
        units: list[PharmacyUnitRecord],
        staff_control: list[PharmacyHodStaffSummaryResponse],
    ) -> list[PharmacyHodUnitAssignmentResponse]:
        members_by_unit: dict[UUID, list[PharmacyHodUnitAssignmentMemberResponse]] = defaultdict(list)
        for staff in staff_control:
            default_unit_id = staff.default_unit_id
            for unit in staff.assigned_units:
                members_by_unit[unit.id].append(
                    PharmacyHodUnitAssignmentMemberResponse(
                        user_id=staff.user_id,
                        full_name=staff.full_name,
                        role=staff.role,
                        is_default=default_unit_id == unit.id,
                        is_active=staff.is_active,
                    )
                )
        payload: list[PharmacyHodUnitAssignmentResponse] = []
        for unit in units:
            if unit.category == PharmacyUnitCategory.STORE:
                continue
            payload.append(
                PharmacyHodUnitAssignmentResponse(
                    unit_id=unit.id,
                    unit_name=unit.name,
                    category=unit.category,
                    members=sorted(
                        members_by_unit.get(unit.id, []),
                        key=lambda item: ((not item.is_default), (item.full_name or "").lower()),
                    ),
                )
            )
        return payload

    def _build_stock_risk_rows(
        self,
        *,
        clinic_id: UUID,
        units: list[PharmacyUnitRecord],
    ) -> list[PharmacyHodStockRiskRowResponse]:
        today = datetime.now(timezone.utc).date()
        expiring_cutoff = today + timedelta(days=self.EXPIRY_SOON_DAYS)
        unit_map = {unit.id: unit for unit in units}
        inventory_items = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == clinic_id,
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
            )
            .all()
        )
        inventory_map = {item.id: item for item in inventory_items}
        lot_rows = (
            self.db.query(PharmacyUnitStockLot)
            .filter(PharmacyUnitStockLot.clinic_id == clinic_id)
            .all()
        )
        grouped: dict[tuple[UUID, UUID], dict] = {}
        for lot in lot_rows:
            key = (lot.service_line_id, lot.inventory_item_id)
            entry = grouped.setdefault(
                key,
                {
                    "unit_id": lot.service_line_id,
                    "item_id": lot.inventory_item_id,
                    "quantity": 0,
                    "earliest_expiry": None,
                    "has_expired": False,
                },
            )
            entry["quantity"] += int(lot.quantity_on_hand)
            if lot.expiry_date is not None:
                if entry["earliest_expiry"] is None or lot.expiry_date < entry["earliest_expiry"]:
                    entry["earliest_expiry"] = lot.expiry_date
                if lot.expiry_date < today and lot.quantity_on_hand > 0:
                    entry["has_expired"] = True

        rows: list[PharmacyHodStockRiskRowResponse] = []
        for (unit_id, item_id), entry in grouped.items():
            inventory_item = inventory_map.get(item_id)
            unit = unit_map.get(unit_id)
            if inventory_item is None or unit is None:
                continue
            quantity = int(entry["quantity"])
            threshold = int(inventory_item.low_stock_threshold)
            earliest_expiry = entry["earliest_expiry"]
            risk_level: str | None = None
            detail = ""
            if entry["has_expired"]:
                risk_level = "EXPIRED"
                detail = "Expired batch is still on hand"
            elif quantity <= 0:
                risk_level = "CRITICAL"
                detail = "No stock on hand"
            elif earliest_expiry is not None and earliest_expiry <= expiring_cutoff:
                risk_level = "EXPIRING_SOON"
                detail = "Batch is approaching expiry"
            elif quantity <= threshold:
                risk_level = "LOW"
                detail = "Stock is below threshold"
            if risk_level is None:
                continue
            rows.append(
                PharmacyHodStockRiskRowResponse(
                    unit_id=unit.id,
                    unit_name=unit.name,
                    item_id=inventory_item.id,
                    item_name=inventory_item.generic_name,
                    quantity_on_hand=quantity,
                    low_stock_threshold=threshold,
                    earliest_expiry_date=earliest_expiry,
                    risk_level=risk_level,
                    detail=detail,
                )
            )

        store_unit = next((unit for unit in units if unit.category == PharmacyUnitCategory.STORE), None)
        for item in inventory_items:
            if any(row.item_id == item.id for row in rows):
                continue
            risk_level: str | None = None
            detail = ""
            quantity = int(item.stock_quantity)
            threshold = int(item.low_stock_threshold)
            if quantity <= 0:
                risk_level = "CRITICAL"
                detail = "No central stock available"
            elif quantity <= threshold:
                risk_level = "LOW"
                detail = "Central stock is below threshold"
            if risk_level is None:
                continue
            rows.append(
                PharmacyHodStockRiskRowResponse(
                    unit_id=store_unit.id if store_unit else None,
                    unit_name=store_unit.name if store_unit else "Central Pharmacy Stock",
                    item_id=item.id,
                    item_name=item.generic_name,
                    quantity_on_hand=quantity,
                    low_stock_threshold=threshold,
                    earliest_expiry_date=None,
                    risk_level=risk_level,
                    detail=detail,
                )
            )

        rows.sort(
            key=lambda row: (
                {"EXPIRED": 0, "CRITICAL": 1, "EXPIRING_SOON": 2, "LOW": 3}[row.risk_level],
                row.unit_name.lower(),
                row.item_name.lower(),
            )
        )
        return rows[:120]

    def _build_critical_alerts(
        self,
        *,
        prescription_rows: list[dict],
        store_supply: list[PharmacyHodRefillRequestRowResponse],
        stock_risk_rows: list[PharmacyHodStockRiskRowResponse],
        generated_at: datetime,
    ) -> list[PharmacyHodCriticalAlertRowResponse]:
        alerts: list[PharmacyHodCriticalAlertRowResponse] = []
        for row in prescription_rows:
            if row["workflow_status"] in OPEN_QUEUE_STATUSES and row["delay_minutes"] >= self.DISPENSE_DELAY_THRESHOLD_MINUTES:
                alerts.append(
                    PharmacyHodCriticalAlertRowResponse(
                        alert_type="DISPENSE_DELAY",
                        severity="critical" if row["workflow_status"] == PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE else "warning",
                        title="Dispense delay threshold exceeded",
                        detail=f"{row['item_name']} has been pending for {row['delay_minutes']} minutes.",
                        unit_id=row["unit_id"],
                        unit_name=row["unit_name"],
                        patient_id=row["patient_id"],
                        patient_name=row["patient_name"],
                        patient_mrn=row["patient_mrn"],
                        occurred_at=row["issued_at"],
                    )
                )
        for row in stock_risk_rows:
            if row.risk_level not in {"CRITICAL", "EXPIRED"}:
                continue
            alerts.append(
                PharmacyHodCriticalAlertRowResponse(
                    alert_type="STOCK_RISK",
                    severity="critical",
                    title=f"{row.risk_level.replace('_', ' ').title()} stock risk",
                    detail=f"{row.item_name} in {row.unit_name}: {row.detail.lower()}.",
                    unit_id=row.unit_id,
                    unit_name=row.unit_name,
                    occurred_at=generated_at,
                )
            )
        for row in store_supply:
            if row.status == PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL and (row.urgency or "").upper() in {"HIGH", "CRITICAL"}:
                alerts.append(
                    PharmacyHodCriticalAlertRowResponse(
                        alert_type="REFILL_URGENCY",
                        severity="warning",
                        title="Urgent refill request awaiting CMD review",
                        detail=f"{row.requesting_unit_name} has an urgent refill request still awaiting CMD approval.",
                        unit_id=row.requesting_unit_id,
                        unit_name=row.requesting_unit_name,
                        occurred_at=row.requested_at,
                    )
                )
        alerts.sort(key=lambda row: (0 if row.severity == "critical" else 1, row.occurred_at), reverse=True)
        return alerts[:30]

    def _build_unit_summary(
        self,
        *,
        units: list[PharmacyUnitRecord],
        prescription_rows: list[dict],
        sales_rows: list[PharmacyHodSalesRevenueRowResponse],
        stock_risk_rows: list[PharmacyHodStockRiskRowResponse],
    ) -> list[PharmacyHodUnitSummaryResponse]:
        revenue_by_unit: dict[UUID | None, int] = defaultdict(int)
        for row in sales_rows:
            revenue_by_unit[row.unit_id] += int(row.amount_minor)
        stock_risk_counts: dict[UUID | None, int] = defaultdict(int)
        for row in stock_risk_rows:
            stock_risk_counts[row.unit_id] += 1
        rows: list[PharmacyHodUnitSummaryResponse] = []
        for unit in units:
            if unit.category == PharmacyUnitCategory.STORE:
                continue
            unit_prescriptions = [item for item in prescription_rows if item["unit_id"] == unit.id]
            rows.append(
                PharmacyHodUnitSummaryResponse(
                    unit_id=unit.id,
                    unit_name=unit.name,
                    category=unit.category,
                    queue_volume=sum(1 for item in unit_prescriptions if item["workflow_status"] in OPEN_QUEUE_STATUSES),
                    ready_to_dispense=sum(1 for item in unit_prescriptions if item["workflow_status"] in ACTIONABLE_READY_STATUSES),
                    awaiting_payment_clearance=sum(1 for item in unit_prescriptions if item["workflow_status"] == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE),
                    stock_risk=stock_risk_counts.get(unit.id, 0),
                    revenue_today_minor=revenue_by_unit.get(unit.id, 0),
                )
            )
        return rows

    def _build_unit_operations(
        self,
        *,
        units: list[PharmacyUnitRecord],
        prescription_rows: list[dict],
        stock_risk_rows: list[PharmacyHodStockRiskRowResponse],
        staff_control: list[PharmacyHodStaffSummaryResponse],
    ) -> list[PharmacyHodUnitOperationResponse]:
        stock_risk_counts: dict[UUID | None, list[PharmacyHodStockRiskRowResponse]] = defaultdict(list)
        for row in stock_risk_rows:
            stock_risk_counts[row.unit_id].append(row)
        staff_counts: dict[UUID, int] = defaultdict(int)
        for staff in staff_control:
            if not staff.is_active:
                continue
            for unit in staff.assigned_units:
                staff_counts[unit.id] += 1
        payload: list[PharmacyHodUnitOperationResponse] = []
        for unit in units:
            if unit.category == PharmacyUnitCategory.STORE:
                continue
            unit_prescriptions = [item for item in prescription_rows if item["unit_id"] == unit.id]
            resolved_minutes = [
                item["delay_minutes"]
                for item in unit_prescriptions
                if item["workflow_status"] in TERMINAL_PRESCRIPTION_STATUSES
            ]
            risk_rows = stock_risk_counts.get(unit.id, [])
            stock_status = "Stable"
            if any(row.risk_level in {"EXPIRED", "CRITICAL"} for row in risk_rows):
                stock_status = "Critical attention"
            elif risk_rows:
                stock_status = "Watchlist"
            bottlenecks: list[str] = []
            queue_volume = sum(1 for item in unit_prescriptions if item["workflow_status"] in OPEN_QUEUE_STATUSES)
            if queue_volume >= self.HIGH_PENDING_THRESHOLD:
                bottlenecks.append("High pending queue")
            if any(item["delay_minutes"] >= self.DISPENSE_DELAY_THRESHOLD_MINUTES for item in unit_prescriptions if item["workflow_status"] in OPEN_QUEUE_STATUSES):
                bottlenecks.append("Dispense delays")
            if any(row.risk_level in {"CRITICAL", "EXPIRED"} for row in risk_rows):
                bottlenecks.append("Stock risk")
            payload.append(
                PharmacyHodUnitOperationResponse(
                    unit_id=unit.id,
                    unit_name=unit.name,
                    category=unit.category,
                    queue_volume=queue_volume,
                    ready_to_dispense=sum(1 for item in unit_prescriptions if item["workflow_status"] in ACTIONABLE_READY_STATUSES),
                    awaiting_payment_clearance=sum(1 for item in unit_prescriptions if item["workflow_status"] == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE),
                    staff_on_duty=staff_counts.get(unit.id, 0),
                    stock_status=stock_status,
                    average_dispense_time_minutes=round(mean(resolved_minutes), 1) if resolved_minutes else None,
                    bottlenecks=bottlenecks,
                )
            )
        return payload

    def _build_bottlenecks(
        self,
        *,
        unit_operations: list[PharmacyHodUnitOperationResponse],
        stock_risk_rows: list[PharmacyHodStockRiskRowResponse],
        critical_alerts: list[PharmacyHodCriticalAlertRowResponse],
    ) -> list[PharmacyHodBottleneckItemResponse]:
        payload: list[PharmacyHodBottleneckItemResponse] = []
        for unit in unit_operations:
            if unit.queue_volume >= self.HIGH_PENDING_THRESHOLD:
                payload.append(
                    PharmacyHodBottleneckItemResponse(
                        severity="warning",
                        title="High pending queue",
                        detail=f"{unit.unit_name} currently carries {unit.queue_volume} active prescription items.",
                        unit_id=unit.unit_id,
                        unit_name=unit.unit_name,
                    )
                )
            if unit.average_dispense_time_minutes and unit.average_dispense_time_minutes >= self.DISPENSE_DELAY_THRESHOLD_MINUTES:
                payload.append(
                    PharmacyHodBottleneckItemResponse(
                        severity="warning",
                        title="Dispense turnaround above threshold",
                        detail=f"Average dispense time in {unit.unit_name} is {unit.average_dispense_time_minutes:.1f} minutes.",
                        unit_id=unit.unit_id,
                        unit_name=unit.unit_name,
                    )
                )
        for risk in stock_risk_rows[:4]:
            if risk.risk_level in {"CRITICAL", "EXPIRED"}:
                payload.append(
                    PharmacyHodBottleneckItemResponse(
                        severity="critical",
                        title=f"{risk.risk_level.replace('_', ' ').title()} stock risk",
                        detail=f"{risk.item_name} in {risk.unit_name} needs attention.",
                        unit_id=risk.unit_id,
                        unit_name=risk.unit_name,
                    )
                )
        if critical_alerts:
            top_alert = critical_alerts[0]
            payload.append(
                PharmacyHodBottleneckItemResponse(
                    severity=top_alert.severity,
                    title=top_alert.title,
                    detail=top_alert.detail,
                    unit_id=top_alert.unit_id,
                    unit_name=top_alert.unit_name,
                )
            )
        return payload[:12]

    def _build_exception_rows(
        self,
        *,
        prescription_rows: list[dict],
        user_map: dict[UUID, User],
    ) -> list[PharmacyHodExceptionOversightRowResponse]:
        rows = []
        for item in prescription_rows:
            if item["exception_authorization_type"] == PharmacyExceptionAuthorizationType.NONE:
                continue
            rows.append(
                PharmacyHodExceptionOversightRowResponse(
                    prescription_id=item["prescription_id"],
                    visit_id=item["visit_id"],
                    patient_id=item["patient_id"],
                    patient_name=item["patient_name"],
                    patient_mrn=item["patient_mrn"],
                    unit_id=item["unit_id"],
                    unit_name=item["unit_name"],
                    exception_type=item["exception_authorization_type"],
                    authorized_by_id=item["authorized_by_id"],
                    authorized_by_name=item["authorized_by_name"],
                    authorized_at=item["authorized_at"],
                    workflow_status=item["workflow_status"],
                    resolution_status=item["status"].value if isinstance(item["status"], PrescriptionStatus) else str(item["status"]),
                )
            )
        rows.sort(key=lambda row: row.authorized_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return rows[:80]

    def _build_finance_rows(
        self,
        *,
        clinic_id: UUID,
        prescription_rows: list[dict],
        start_dt: datetime,
        end_dt: datetime,
    ) -> tuple[PharmacyHodSalesRevenueResponse, list[PharmacyHodReceiptRegisterRowResponse]]:
        prescriptions_by_billing_item: dict[UUID, dict] = {}
        for row in prescription_rows:
            billing_item_id = row.get("billing_item_id")
            if billing_item_id is None:
                continue
            prescriptions_by_billing_item[billing_item_id] = row

        receipt_items = (
            self.db.query(PaymentReceiptItem, PaymentReceipt, BillingItem)
            .join(PaymentReceipt, PaymentReceipt.id == PaymentReceiptItem.receipt_id)
            .join(BillingItem, BillingItem.id == PaymentReceiptItem.billing_item_id)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= start_dt,
                PaymentReceipt.occurred_at < end_dt,
                BillingItem.service_type == "MEDICATION",
            )
            .order_by(PaymentReceipt.occurred_at.desc())
            .all()
        )
        patient_context = self._load_patient_context(
            clinic_id=clinic_id,
            visit_ids=[receipt.visit_id for _, receipt, _ in receipt_items],
        )
        pay_point_ids = {receipt.cashier_pay_point_id for _, receipt, _ in receipt_items if receipt.cashier_pay_point_id}
        pay_points = (
            self.db.query(CashierPayPoint)
            .filter(CashierPayPoint.id.in_(pay_point_ids))
            .all()
            if pay_point_ids
            else []
        )
        pay_point_map = {row.id: row for row in pay_points}
        cashier_ids = {receipt.collected_by for _, receipt, _ in receipt_items}
        cashiers = self.db.query(User).filter(User.id.in_(cashier_ids)).all() if cashier_ids else []
        cashier_map = {row.id: row for row in cashiers}

        sales_rows: list[PharmacyHodSalesRevenueRowResponse] = []
        receipt_register_map: dict[UUID, dict] = {}
        revenue_by_unit: dict[tuple[UUID | None, str], int] = defaultdict(int)
        currency = "NGN"
        for receipt_item, receipt, billing_item in receipt_items:
            currency = receipt.currency or currency
            prescription_row = prescriptions_by_billing_item.get(billing_item.id)
            patient_ctx = patient_context.get(receipt.visit_id, {})
            pay_point = pay_point_map.get(receipt.cashier_pay_point_id)
            cashier = cashier_map.get(receipt.collected_by)
            unit_id = prescription_row["unit_id"] if prescription_row else None
            unit_name = prescription_row["unit_name"] if prescription_row else None
            sales_row = PharmacyHodSalesRevenueRowResponse(
                receipt_id=receipt.id,
                receipt_number=receipt.receipt_number,
                occurred_at=receipt.occurred_at,
                patient_id=patient_ctx.get("patient_id"),
                patient_name=patient_ctx.get("patient_name"),
                patient_mrn=patient_ctx.get("patient_mrn"),
                visit_id=receipt.visit_id,
                item_name=billing_item.item_name,
                unit_id=unit_id,
                unit_name=unit_name,
                cashier_pay_point_id=receipt.cashier_pay_point_id,
                cashier_pay_point_name=pay_point.name if pay_point else None,
                amount_minor=int(receipt_item.amount_minor),
                currency=receipt.currency,
                cashier_name=cashier.full_name if cashier else None,
            )
            sales_rows.append(sales_row)
            revenue_by_unit[(unit_id, unit_name or "Unassigned")] += int(receipt_item.amount_minor)
            receipt_entry = receipt_register_map.setdefault(
                receipt.id,
                {
                    "receipt_id": receipt.id,
                    "receipt_number": receipt.receipt_number,
                    "occurred_at": receipt.occurred_at,
                    "patient_id": patient_ctx.get("patient_id"),
                    "patient_name": patient_ctx.get("patient_name"),
                    "patient_mrn": patient_ctx.get("patient_mrn"),
                    "visit_id": receipt.visit_id,
                    "amount_minor": int(receipt.total_amount_minor),
                    "currency": receipt.currency,
                    "cashier_name": cashier.full_name if cashier else None,
                    "cashier_pay_point_name": pay_point.name if pay_point else None,
                    "unit_names": set(),
                    "linked_items": [],
                },
            )
            if unit_name:
                receipt_entry["unit_names"].add(unit_name)
            receipt_entry["linked_items"].append(billing_item.item_name)

        receipt_register = [
            PharmacyHodReceiptRegisterRowResponse(
                receipt_id=value["receipt_id"],
                receipt_number=value["receipt_number"],
                occurred_at=value["occurred_at"],
                patient_id=value["patient_id"],
                patient_name=value["patient_name"],
                patient_mrn=value["patient_mrn"],
                visit_id=value["visit_id"],
                amount_minor=value["amount_minor"],
                currency=value["currency"],
                cashier_name=value["cashier_name"],
                cashier_pay_point_name=value["cashier_pay_point_name"],
                unit_names=sorted(value["unit_names"]),
                linked_items=value["linked_items"],
            )
            for value in receipt_register_map.values()
        ]
        receipt_register.sort(key=lambda row: row.occurred_at, reverse=True)

        revenue_by_unit_rows = [
            PharmacyHodSalesRevenueByUnitResponse(
                unit_id=unit_id,
                unit_name=unit_name,
                revenue_minor=amount,
            )
            for (unit_id, unit_name), amount in revenue_by_unit.items()
        ]
        revenue_by_unit_rows.sort(key=lambda row: row.revenue_minor, reverse=True)

        sales_revenue = PharmacyHodSalesRevenueResponse(
            total_revenue_minor=sum(row.amount_minor for row in sales_rows),
            receipt_count=len(receipt_register),
            paid_item_count=len(sales_rows),
            currency=currency,
            revenue_by_unit=revenue_by_unit_rows,
            rows=sales_rows[:120],
        )
        return sales_revenue, receipt_register[:120]

    def _build_pay_point_performance(
        self,
        *,
        clinic_id: UUID,
        sales_rows: list[PharmacyHodSalesRevenueRowResponse],
        prescription_rows: list[dict],
        currency: str,
    ) -> list[PharmacyHodPayPointPerformanceResponse]:
        pay_points = (
            self.db.query(CashierPayPoint)
            .filter(CashierPayPoint.clinic_id == clinic_id, CashierPayPoint.is_active == True)
            .order_by(CashierPayPoint.name.asc())
            .all()
        )
        transactions_by_pay_point: dict[UUID, int] = defaultdict(int)
        revenue_by_pay_point: dict[UUID, int] = defaultdict(int)
        awaiting_by_pay_point: dict[UUID, int] = defaultdict(int)
        for row in sales_rows:
            if row.cashier_pay_point_id is None:
                continue
            transactions_by_pay_point[row.cashier_pay_point_id] += 1
            revenue_by_pay_point[row.cashier_pay_point_id] += int(row.amount_minor)
        for row in prescription_rows:
            pay_point_id = row["assigned_cashier_pay_point_id"]
            if pay_point_id is None:
                continue
            if row["workflow_status"] == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE:
                awaiting_by_pay_point[pay_point_id] += 1
        return [
            PharmacyHodPayPointPerformanceResponse(
                pay_point_id=pay_point.id,
                pay_point_name=pay_point.name,
                transaction_count=transactions_by_pay_point.get(pay_point.id, 0),
                revenue_minor=revenue_by_pay_point.get(pay_point.id, 0),
                awaiting_clearance_count=awaiting_by_pay_point.get(pay_point.id, 0),
                currency=currency,
            )
            for pay_point in pay_points
        ]

    def _build_activity_audit(
        self,
        *,
        clinic_id: UUID,
        unit_map: dict[UUID, PharmacyUnitRecord],
        user_map: dict[UUID, User],
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[PharmacyHodActivityAuditRowResponse]:
        events = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type.in_(PHARMACY_EVENT_TYPES),
                EventLog.created_at >= start_dt,
                EventLog.created_at < end_dt,
            )
            .order_by(EventLog.created_at.desc())
            .all()
        )
        fulfillment_rows = (
            self.db.query(PrescriptionFulfillmentEvent, Prescription)
            .join(Prescription, Prescription.id == PrescriptionFulfillmentEvent.prescription_id)
            .filter(
                PrescriptionFulfillmentEvent.clinic_id == clinic_id,
                PrescriptionFulfillmentEvent.occurred_at >= start_dt,
                PrescriptionFulfillmentEvent.occurred_at < end_dt,
            )
            .order_by(PrescriptionFulfillmentEvent.occurred_at.desc())
            .all()
        )
        patient_context = self._load_patient_context(
            clinic_id=clinic_id,
            visit_ids=[prescription.visit_id for _, prescription in fulfillment_rows],
        )
        rows: list[PharmacyHodActivityAuditRowResponse] = []
        for event in events:
            payload = self._parse_event_payload(event.payload)
            unit_id = self._uuid_from_payload(payload.get("requesting_unit_id") or payload.get("target_unit_id") or payload.get("receiving_unit_id"))
            unit = unit_map.get(unit_id) if unit_id else None
            actor = user_map.get(event.actor_id) if event.actor_id else None
            rows.append(
                PharmacyHodActivityAuditRowResponse(
                    id=str(event.id),
                    source_type="event_log",
                    action_type=event.event_type,
                    occurred_at=event.created_at,
                    actor_id=event.actor_id,
                    actor_name=actor.full_name if actor else None,
                    actor_role=event.actor_role,
                    unit_id=unit_id,
                    unit_name=unit.name if unit else None,
                    patient_id=event.patient_id,
                    summary=self._event_summary(event),
                    detail=self._event_detail(event, payload),
                    severity=self._event_severity(event.event_type, payload),
                )
            )
        for fulfillment, prescription in fulfillment_rows:
            if fulfillment.fulfillment_type == PrescriptionFulfillmentType.DISPENSED_IN_HOUSE:
                continue
            patient_ctx = patient_context.get(prescription.visit_id, {})
            actor = user_map.get(fulfillment.actor_id)
            unit = unit_map.get(prescription.assigned_dispensing_unit_id)
            rows.append(
                PharmacyHodActivityAuditRowResponse(
                    id=str(fulfillment.id),
                    source_type="fulfillment",
                    action_type=fulfillment.fulfillment_type.value,
                    occurred_at=fulfillment.occurred_at,
                    actor_id=fulfillment.actor_id,
                    actor_name=actor.full_name if actor else None,
                    actor_role=actor.role if actor else None,
                    unit_id=prescription.assigned_dispensing_unit_id,
                    unit_name=unit.name if unit else None,
                    patient_id=patient_ctx.get("patient_id"),
                    patient_name=patient_ctx.get("patient_name"),
                    patient_mrn=patient_ctx.get("patient_mrn"),
                    summary=(
                        f"Dispensed {prescription.drug_name}"
                        if fulfillment.fulfillment_type == PrescriptionFulfillmentType.DISPENSED_IN_HOUSE
                        else f"Externally fulfilled {prescription.drug_name}"
                    ),
                    detail=fulfillment.note,
                    severity="info",
                )
            )
        rows.sort(key=lambda row: row.occurred_at, reverse=True)
        return rows[: self.MAX_ACTIVITY_ROWS]

    def _build_staff_performance(
        self,
        *,
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
        staff_control: list[PharmacyHodStaffSummaryResponse],
        prescription_rows: list[dict],
        user_map: dict[UUID, User],
    ) -> list[PharmacyHodStaffPerformanceResponse]:
        reassignment_events = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type == "PHARMACY_REASSIGNED",
                EventLog.created_at >= start_dt,
                EventLog.created_at < end_dt,
            )
            .all()
        )
        stock_events = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type.in_(
                    {
                        "PHARMACY_REFILL_REQUESTED",
                        "PHARMACY_ISSUE_VOUCHER_GENERATED",
                        "PHARMACY_ISSUE_DISPATCHED",
                        "PHARMACY_ACKNOWLEDGEMENT_RECORDED",
                    }
                ),
                EventLog.created_at >= start_dt,
                EventLog.created_at < end_dt,
            )
            .all()
        )
        reassignment_count_by_user: dict[UUID, int] = defaultdict(int)
        stock_event_count_by_user: dict[UUID, int] = defaultdict(int)
        activity_count_by_user: dict[UUID, int] = defaultdict(int)
        for event in reassignment_events:
            if event.actor_id:
                reassignment_count_by_user[event.actor_id] += 1
                activity_count_by_user[event.actor_id] += 1
        for event in stock_events:
            if event.actor_id:
                stock_event_count_by_user[event.actor_id] += 1
                activity_count_by_user[event.actor_id] += 1

        payload: list[PharmacyHodStaffPerformanceResponse] = []
        for staff in staff_control:
            handled = [
                row
                for row in prescription_rows
                if row["assigned_staff_id"] == staff.user_id and row["resolved_at"] is not None and row["resolved_at"] >= start_dt and row["resolved_at"] < end_dt
            ]
            turnaround_values = [row["delay_minutes"] for row in handled]
            pending_load = sum(
                1
                for row in prescription_rows
                if row["unit_id"] in {unit.id for unit in staff.assigned_units}
                and row["workflow_status"] in OPEN_QUEUE_STATUSES
            )
            payload.append(
                PharmacyHodStaffPerformanceResponse(
                    user_id=staff.user_id,
                    full_name=staff.full_name,
                    role=staff.role,
                    assigned_units=[unit.name for unit in staff.assigned_units],
                    prescriptions_handled=len(handled),
                    average_dispense_time_minutes=round(mean(turnaround_values), 1) if turnaround_values else None,
                    pending_load=pending_load,
                    reassignment_count=reassignment_count_by_user.get(staff.user_id, 0),
                    stock_issue_events=stock_event_count_by_user.get(staff.user_id, 0),
                    shift_activity_count=activity_count_by_user.get(staff.user_id, 0) + len(handled),
                )
            )
        payload.sort(key=lambda row: (row.prescriptions_handled, row.shift_activity_count), reverse=True)
        return payload

    def _build_system_health(
        self,
        *,
        prescription_rows: list[dict],
        critical_alerts: list[PharmacyHodCriticalAlertRowResponse],
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[PharmacyHodSystemHealthResponse]:
        missing_links = sum(
            1
            for row in prescription_rows
            if row["payment_state"] == "UNLINKED" or row["unit_id"] is None or row["assigned_cashier_pay_point_id"] is None
        )
        payment_sync_mismatch = sum(
            1
            for row in prescription_rows
            if row["payment_state"] == BillingItemStatus.PAID.value
            and row["workflow_status"] not in {
                PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
                PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
                PharmacyPrescriptionWorkflowStatus.DISPENSED,
                PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED,
            }
        )
        legacy_dispenses = (
            self.db.query(PharmacyStockMovement)
            .filter(
                PharmacyStockMovement.clinic_id == clinic_id,
                PharmacyStockMovement.movement_type == "DISPENSE",
                PharmacyStockMovement.occurred_at >= start_dt,
                PharmacyStockMovement.occurred_at < end_dt,
                PharmacyStockMovement.note.like("%legacy clinic inventory fallback%"),
            )
            .count()
        )
        return [
            PharmacyHodSystemHealthResponse(
                key="pharmacy_flow",
                label="Pharmacy Flow",
                status="ATTENTION" if missing_links else "OK",
                detail=(
                    f"{missing_links} prescription item(s) are missing billing or routing linkage."
                    if missing_links
                    else "Prescription routing and billing linkage are in sync."
                ),
            ),
            PharmacyHodSystemHealthResponse(
                key="payment_sync",
                label="Payment Sync",
                status="ATTENTION" if payment_sync_mismatch else "OK",
                detail=(
                    f"{payment_sync_mismatch} paid pharmacy item(s) are not yet in a ready terminal path."
                    if payment_sync_mismatch
                    else "Cashier payment state and pharmacy readiness are aligned."
                ),
            ),
            PharmacyHodSystemHealthResponse(
                key="stock_sync",
                label="Stock Sync",
                status="ATTENTION" if legacy_dispenses or critical_alerts else "OK",
                detail=(
                    f"{legacy_dispenses} legacy dispense movement(s) bypassed unit lots in this range."
                    if legacy_dispenses
                    else "No legacy stock fallback was used in this reporting window."
                ),
            ),
        ]

    def _build_refill_frequency(
        self,
        *,
        store_supply: list[PharmacyHodRefillRequestRowResponse],
    ) -> list[PharmacyHodSalesRevenueByUnitResponse]:
        counts: dict[tuple[UUID, str], int] = defaultdict(int)
        for row in store_supply:
            counts[(row.requesting_unit_id, row.requesting_unit_name)] += 1
        payload = [
            PharmacyHodSalesRevenueByUnitResponse(
                unit_id=unit_id,
                unit_name=unit_name,
                revenue_minor=count,
            )
            for (unit_id, unit_name), count in counts.items()
        ]
        payload.sort(key=lambda row: row.revenue_minor, reverse=True)
        return payload

    def _build_turnaround_analytics(
        self,
        *,
        unit_operations: list[PharmacyHodUnitOperationResponse],
    ) -> list[PharmacyHodSalesRevenueByUnitResponse]:
        payload = []
        for unit in unit_operations:
            if unit.average_dispense_time_minutes is None:
                continue
            payload.append(
                PharmacyHodSalesRevenueByUnitResponse(
                    unit_id=unit.unit_id,
                    unit_name=unit.unit_name,
                    revenue_minor=int(round(unit.average_dispense_time_minutes)),
                )
            )
        payload.sort(key=lambda row: row.revenue_minor, reverse=True)
        return payload

    def _build_stock_risk_counts(
        self,
        *,
        stock_risk_rows: list[PharmacyHodStockRiskRowResponse],
    ) -> list[dict[str, int | str]]:
        counts: dict[str, int] = defaultdict(int)
        for row in stock_risk_rows:
            counts[row.risk_level] += 1
        return [
            {"label": key, "count": count}
            for key, count in sorted(counts.items(), key=lambda item: item[0])
        ]

    def _parse_event_payload(self, payload: str | None) -> dict:
        if not payload:
            return {}
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _uuid_from_payload(self, value) -> UUID | None:
        if not value:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    def _event_summary(self, event: EventLog | None) -> str:
        if event is None:
            return ""
        return {
            "PHARMACY_REFILL_REQUESTED": "Refill request submitted",
            "PHARMACY_CATALOG_REQUEST_SUBMITTED": "Catalog request submitted",
            "PHARMACY_CATALOG_CMD_APPROVED": "CMD approved catalog request",
            "PHARMACY_CATALOG_CMD_REJECTED": "CMD rejected catalog request",
            "PHARMACY_CATALOG_PRICED": "Accounts configured pharmacy pricing",
            "PHARMACY_CATALOG_ACTIVATED": "Catalog item activated for operations",
            "PHARMACY_CATALOG_DEACTIVATED": "Catalog item deactivated",
            "PHARMACY_CMD_APPROVED": "CMD approved supply request",
            "PHARMACY_CMD_REJECTED": "CMD rejected supply request",
            "PHARMACY_ISSUE_VOUCHER_GENERATED": "Issue voucher generated",
            "PHARMACY_ISSUE_DISPATCHED": "Store dispatched issued stock",
            "PHARMACY_ACKNOWLEDGEMENT_RECORDED": "Unit acknowledged issued stock",
            "PHARMACY_REASSIGNED": "Prescription reassigned",
            "PHARMACY_PARTIAL_DISPENSED": "Prescription partially dispensed",
            "PHARMACY_FULLY_DISPENSED": "Prescription fully dispensed",
            "PHARMACY_STAFF_ASSIGNMENT_UPDATED": "Pharmacy staff assignment updated",
        }.get(event.event_type, event.event_type.replace("_", " ").title())

    def _event_detail(self, event: EventLog, payload: dict) -> str | None:
        if event.event_type == "PHARMACY_REASSIGNED":
            return payload.get("reason")
        if event.event_type == "PHARMACY_PARTIAL_DISPENSED":
            return (
                f"{payload.get('quantity_dispensed')} dispensed, "
                f"{payload.get('quantity_remaining')} remaining."
            )
        if event.event_type == "PHARMACY_FULLY_DISPENSED":
            return f"{payload.get('quantity_dispensed')} dispensed to complete the prescription."
        if event.event_type in {
            "PHARMACY_CMD_APPROVED",
            "PHARMACY_CMD_REJECTED",
            "PHARMACY_CATALOG_CMD_APPROVED",
            "PHARMACY_CATALOG_CMD_REJECTED",
        }:
            return payload.get("decision")
        if event.event_type in {
            "PHARMACY_CATALOG_PRICED",
            "PHARMACY_CATALOG_ACTIVATED",
            "PHARMACY_CATALOG_DEACTIVATED",
        }:
            return payload.get("catalog_code")
        if event.event_type == "PHARMACY_STAFF_ASSIGNMENT_UPDATED":
            return payload.get("target_user_name")
        return None

    def _event_severity(self, event_type: str, payload: dict) -> str:
        if event_type in {
            "PHARMACY_REASSIGNED",
            "PHARMACY_CMD_REJECTED",
            "PHARMACY_CATALOG_CMD_REJECTED",
            "PHARMACY_PARTIAL_DISPENSED",
        }:
            return "warning"
        if event_type in {
            "PHARMACY_ACKNOWLEDGEMENT_RECORDED",
            "PHARMACY_CMD_APPROVED",
            "PHARMACY_CATALOG_CMD_APPROVED",
            "PHARMACY_CATALOG_PRICED",
            "PHARMACY_CATALOG_ACTIVATED",
            "PHARMACY_CATALOG_REQUEST_SUBMITTED",
        }:
            return "info"
        if event_type == "PHARMACY_STAFF_ASSIGNMENT_UPDATED":
            return "info"
        return "info"
