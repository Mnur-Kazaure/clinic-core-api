from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from app.models.billing_item import BillingItem
from app.models.cashier_pay_point import CashierPayPoint
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.payment_receipt import PaymentReceipt
from app.models.payment_receipt_item import PaymentReceiptItem
from app.models.prescription import Prescription
from app.models.receipt_reprint_log import ReceiptReprintLog
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.shared.enums import BillingItemStatus, MRNStatus, PharmacyExceptionAuthorizationType, PharmacyPrescriptionWorkflowStatus


class CashierDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> dict:
        pending_items = self._load_pending_items(
            clinic_id=clinic_id,
            cashier_pay_point_id=cashier_pay_point_id,
            limit=max(limit * 5, 250),
        )
        visits = self._load_visits({item.visit_id for item in pending_items})
        patients = self._load_patients(
            patient_ids={item.patient_id for item in pending_items},
        )
        service_lines = self._load_service_lines(
            {
                visit.service_line_id
                for visit in visits.values()
                if visit.service_line_id is not None
            }
        )
        pay_points = self._load_pay_points(
            {
                item.cashier_pay_point_id
                for item in pending_items
                if item.cashier_pay_point_id is not None
            }
        )
        prescriptions_by_item = self._load_prescriptions_by_billing_item(
            billing_item_ids={item.id for item in pending_items}
        )
        dispensing_units = self._load_service_lines(
            {
                prescription.assigned_dispensing_unit_id
                for prescription in prescriptions_by_item.values()
                if prescription.assigned_dispensing_unit_id is not None
            }
        )

        charge_rows = [
            self._build_charge_row(
                item=item,
                visit=visits.get(item.visit_id),
                patient=patients.get(item.patient_id),
                source_service_lines=service_lines,
                pay_points=pay_points,
                prescription=prescriptions_by_item.get(item.id),
                dispensing_units=dispensing_units,
            )
            for item in pending_items
        ]
        filtered_charge_rows = self._filter_charge_rows(charge_rows, search=search)

        receipts = self._load_receipts(
            clinic_id=clinic_id,
            cashier_pay_point_id=cashier_pay_point_id,
            search=search,
            limit=20,
        )
        receipt_rows = self._build_receipt_rows(receipts=receipts)

        transactions = self._load_transactions(
            clinic_id=clinic_id,
            cashier_pay_point_id=cashier_pay_point_id,
            search=search,
            limit=20,
        )
        transaction_rows = self._build_transaction_rows(transactions=transactions)

        exception_rows = self._build_exception_rows(
            clinic_id=clinic_id,
            cashier_pay_point_id=cashier_pay_point_id,
            search=search,
            limit=20,
        )

        activity_rows = self._build_activity_rows(
            clinic_id=clinic_id,
            cashier_pay_point_id=cashier_pay_point_id,
            search=search,
            limit=25,
            receipt_rows=receipt_rows,
        )

        currency = self._resolve_currency(
            clinic_id=clinic_id,
            charge_rows=filtered_charge_rows,
            receipt_rows=receipt_rows,
        )

        now = datetime.now(timezone.utc)
        today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        today_end = today_start + timedelta(days=1)
        paid_today_minor, receipts_today = self._load_today_receipt_totals(
            clinic_id=clinic_id,
            cashier_pay_point_id=cashier_pay_point_id,
            start=today_start,
            end=today_end,
        )

        pharmacy_rows = [row for row in filtered_charge_rows if row["service_type"] == "MEDICATION"]
        laboratory_rows = [row for row in filtered_charge_rows if row["service_type"] == "LAB_TEST"]

        return {
            "overview": {
                "pending_charges_count": len(filtered_charge_rows),
                "pharmacy_charges_pending": len(pharmacy_rows),
                "laboratory_charges_pending": len(laboratory_rows),
                "paid_today_minor": paid_today_minor,
                "receipts_today": receipts_today,
                "active_queue": len({row["visit_id"] for row in filtered_charge_rows}),
                "currency": currency,
                "last_updated_at": now,
            },
            "pending_charges": filtered_charge_rows[:limit],
            "pharmacy_charges": pharmacy_rows[:limit],
            "laboratory_charges": laboratory_rows[:limit],
            "receipts": receipt_rows,
            "transactions": transaction_rows,
            "exceptions_holds": exception_rows,
            "activity_audit": activity_rows,
        }

    def snapshot_signature(self, snapshot: dict) -> str:
        payload = jsonable_encoder(snapshot)
        if isinstance(payload, dict) and isinstance(payload.get("overview"), dict):
            payload["overview"]["last_updated_at"] = None
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _load_pending_items(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None,
        limit: int,
    ) -> list[BillingItem]:
        query = (
            self.db.query(BillingItem)
            .filter(
                BillingItem.clinic_id == clinic_id,
                BillingItem.status == BillingItemStatus.PENDING,
            )
            .order_by(BillingItem.created_at.desc())
        )
        if cashier_pay_point_id is not None:
            query = query.filter(
                (BillingItem.cashier_pay_point_id == cashier_pay_point_id)
                | (BillingItem.cashier_pay_point_id.is_(None))
            )
        return query.limit(limit).all()

    def _load_visits(self, visit_ids: set[UUID]) -> dict[UUID, Visit]:
        if not visit_ids:
            return {}
        rows = self.db.query(Visit).filter(Visit.id.in_(visit_ids)).all()
        return {row.id: row for row in rows}

    def _load_patients(self, *, patient_ids: set[UUID]) -> dict[UUID, dict]:
        if not patient_ids:
            return {}
        patients = self.db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
        mrn_rows = (
            self.db.query(PatientMRN.patient_id, PatientMRN.mrn)
            .filter(
                PatientMRN.patient_id.in_(patient_ids),
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .all()
        )
        mrn_map = {patient_id: mrn for patient_id, mrn in mrn_rows}
        return {
            patient.id: {
                "full_name": patient.full_name,
                "mrn": mrn_map.get(patient.id),
            }
            for patient in patients
        }

    def _load_service_lines(self, service_line_ids: set[UUID | None]) -> dict[UUID, ServiceLine]:
        ids = [service_line_id for service_line_id in service_line_ids if service_line_id is not None]
        if not ids:
            return {}
        rows = self.db.query(ServiceLine).filter(ServiceLine.id.in_(ids)).all()
        return {row.id: row for row in rows}

    def _load_pay_points(self, pay_point_ids: set[UUID]) -> dict[UUID, CashierPayPoint]:
        if not pay_point_ids:
            return {}
        rows = self.db.query(CashierPayPoint).filter(CashierPayPoint.id.in_(pay_point_ids)).all()
        return {row.id: row for row in rows}

    def _load_prescriptions_by_billing_item(
        self,
        *,
        billing_item_ids: set[UUID],
    ) -> dict[UUID, Prescription]:
        if not billing_item_ids:
            return {}
        rows = (
            self.db.query(Prescription)
            .filter(Prescription.billing_item_id.in_(billing_item_ids))
            .all()
        )
        return {
            row.billing_item_id: row
            for row in rows
            if row.billing_item_id is not None
        }

    def _build_charge_row(
        self,
        *,
        item: BillingItem,
        visit: Visit | None,
        patient: dict | None,
        source_service_lines: dict[UUID, ServiceLine],
        pay_points: dict[UUID, CashierPayPoint],
        prescription: Prescription | None,
        dispensing_units: dict[UUID, ServiceLine],
    ) -> dict:
        patient_name = patient.get("full_name") if patient else None
        patient_mrn = patient.get("mrn") if patient else None
        pay_point = pay_points.get(item.cashier_pay_point_id) if item.cashier_pay_point_id else None
        source_department_name = self._resolve_source_department_name(
            visit=visit,
            source_service_lines=source_service_lines,
        )
        assigned_unit = (
            dispensing_units.get(prescription.assigned_dispensing_unit_id)
            if prescription and prescription.assigned_dispensing_unit_id
            else None
        )
        destination_hint = None
        if assigned_unit is not None:
            if (
                prescription is not None
                and prescription.workflow_status == PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE
            ):
                if (
                    prescription.exception_authorization_type is not None
                    and prescription.exception_authorization_type != PharmacyExceptionAuthorizationType.NONE
                    and item.status != BillingItemStatus.PAID
                ):
                    destination_hint = f"Exception Authorized — {assigned_unit.name}"
                else:
                    destination_hint = f"Ready for Pharmacy Dispense — {assigned_unit.name}"
            else:
                destination_hint = f"Awaiting Payment Clearance — {assigned_unit.name}"

        return {
            "billing_item_id": item.id,
            "visit_id": item.visit_id,
            "patient_id": item.patient_id,
            "patient_name": patient_name,
            "patient_mrn": patient_mrn,
            "source_department_name": source_department_name,
            "item_name": item.item_name,
            "quantity": int(item.quantity),
            "amount_minor": int(item.total_minor - item.amount_paid_minor),
            "currency": item.currency,
            "service_type": item.service_type,
            "payment_status": "UNPAID",
            "cashier_pay_point_id": item.cashier_pay_point_id,
            "cashier_pay_point_name": pay_point.name if pay_point else None,
            "assigned_dispensing_unit_id": assigned_unit.id if assigned_unit else None,
            "assigned_dispensing_unit_name": assigned_unit.name if assigned_unit else None,
            "pharmacy_readiness_state": prescription.workflow_status if prescription else None,
            "exception_authorization_type": (
                prescription.exception_authorization_type if prescription else None
            ),
            "destination_hint": destination_hint,
            "created_at": item.created_at,
        }

    def _resolve_source_department_name(
        self,
        *,
        visit: Visit | None,
        source_service_lines: dict[UUID, ServiceLine],
    ) -> str | None:
        if visit is None:
            return None
        if visit.service_line_id and visit.service_line_id in source_service_lines:
            return source_service_lines[visit.service_line_id].name
        if visit.service_line is not None:
            return visit.service_line.value.replace("_", " ").title()
        return None

    def _filter_charge_rows(self, rows: list[dict], *, search: str | None) -> list[dict]:
        if not search or not search.strip():
            return rows
        term = search.strip().lower()
        filtered: list[dict] = []
        for row in rows:
            haystack = [
                row.get("patient_name"),
                row.get("patient_mrn"),
                row.get("item_name"),
                row.get("source_department_name"),
                str(row.get("visit_id")) if row.get("visit_id") else None,
                row.get("assigned_dispensing_unit_name"),
                row.get("cashier_pay_point_name"),
            ]
            if any(term in str(value).lower() for value in haystack if value):
                filtered.append(row)
        return filtered

    def _load_receipts(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None,
        search: str | None,
        limit: int,
    ):
        query = (
            self.db.query(
                PaymentReceipt,
                Patient.full_name.label("patient_name"),
                User.full_name.label("collected_by_name"),
            )
            .join(
                Patient,
                (Patient.id == PaymentReceipt.patient_id)
                & (Patient.clinic_id == PaymentReceipt.clinic_id),
            )
            .join(User, User.id == PaymentReceipt.collected_by)
            .filter(PaymentReceipt.clinic_id == clinic_id)
        )
        if cashier_pay_point_id is not None:
            query = query.filter(PaymentReceipt.cashier_pay_point_id == cashier_pay_point_id)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Patient.full_name).like(term))
                | (func.lower(PaymentReceipt.receipt_number).like(term))
                | (cast(PaymentReceipt.visit_id, String).like(term))
            )
        return query.order_by(PaymentReceipt.occurred_at.desc()).limit(limit).all()

    def _build_receipt_rows(self, *, receipts) -> list[dict]:
        receipt_ids = {receipt.id for receipt, _patient_name, _cashier_name in receipts}
        pay_point_ids = {
            receipt.cashier_pay_point_id
            for receipt, _patient_name, _cashier_name in receipts
            if receipt.cashier_pay_point_id is not None
        }
        patient_ids = {receipt.patient_id for receipt, _patient_name, _cashier_name in receipts}

        pay_points = self._load_pay_points(pay_point_ids)
        patients = self._load_patients(patient_ids=patient_ids)

        item_rows = (
            self.db.query(PaymentReceiptItem, BillingItem)
            .join(
                BillingItem,
                (BillingItem.id == PaymentReceiptItem.billing_item_id)
                & (BillingItem.clinic_id == PaymentReceiptItem.clinic_id),
            )
            .filter(PaymentReceiptItem.receipt_id.in_(receipt_ids))
            .all()
            if receipt_ids
            else []
        )
        receipt_items: dict[UUID, list[BillingItem]] = {}
        billing_item_ids: set[UUID] = set()
        for alloc, item in item_rows:
            receipt_items.setdefault(alloc.receipt_id, []).append(item)
            billing_item_ids.add(item.id)

        prescriptions = self._load_prescriptions_by_billing_item(billing_item_ids=billing_item_ids)
        dispensing_units = self._load_service_lines(
            {
                prescription.assigned_dispensing_unit_id
                for prescription in prescriptions.values()
                if prescription.assigned_dispensing_unit_id is not None
            }
        )

        rows: list[dict] = []
        for receipt, patient_name, collected_by_name in receipts:
            patient = patients.get(receipt.patient_id)
            linked_items = [item.item_name for item in receipt_items.get(receipt.id, [])]
            destination_hints: list[str] = []
            for item in receipt_items.get(receipt.id, []):
                prescription = prescriptions.get(item.id)
                if prescription is None or prescription.assigned_dispensing_unit_id is None:
                    continue
                unit = dispensing_units.get(prescription.assigned_dispensing_unit_id)
                if unit is None:
                    continue
                hint = f"Ready for Pharmacy Dispense — {unit.name}"
                if hint not in destination_hints:
                    destination_hints.append(hint)
            pay_point = pay_points.get(receipt.cashier_pay_point_id) if receipt.cashier_pay_point_id else None
            rows.append(
                {
                    "receipt_id": receipt.id,
                    "receipt_number": receipt.receipt_number,
                    "visit_id": receipt.visit_id,
                    "patient_id": receipt.patient_id,
                    "patient_name": patient_name or (patient.get("full_name") if patient else None),
                    "patient_mrn": patient.get("mrn") if patient else None,
                    "amount_minor": int(receipt.total_amount_minor),
                    "currency": receipt.currency,
                    "payment_method": receipt.payment_method,
                    "cashier_pay_point_id": receipt.cashier_pay_point_id,
                    "cashier_pay_point_name": pay_point.name if pay_point else None,
                    "collected_by_name": collected_by_name,
                    "linked_items": linked_items,
                    "destination_hints": destination_hints,
                    "occurred_at": receipt.occurred_at,
                }
            )
        return rows

    def _load_transactions(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None,
        search: str | None,
        limit: int,
    ):
        query = (
            self.db.query(
                PaymentReceipt,
                Patient.full_name.label("patient_name"),
                User.full_name.label("collected_by_name"),
            )
            .join(
                Patient,
                (Patient.id == PaymentReceipt.patient_id)
                & (Patient.clinic_id == PaymentReceipt.clinic_id),
            )
            .join(User, User.id == PaymentReceipt.collected_by)
            .filter(PaymentReceipt.clinic_id == clinic_id)
        )
        if cashier_pay_point_id is not None:
            query = query.filter(PaymentReceipt.cashier_pay_point_id == cashier_pay_point_id)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Patient.full_name).like(term))
                | (func.lower(PaymentReceipt.receipt_number).like(term))
                | (cast(PaymentReceipt.visit_id, String).like(term))
            )
        return query.order_by(PaymentReceipt.occurred_at.desc()).limit(limit).all()

    def _build_transaction_rows(self, *, transactions) -> list[dict]:
        patient_ids = {receipt.patient_id for receipt, _patient_name, _cashier_name in transactions}
        patients = self._load_patients(patient_ids=patient_ids)
        pay_points = self._load_pay_points(
            {
                receipt.cashier_pay_point_id
                for receipt, _patient_name, _cashier_name in transactions
                if receipt.cashier_pay_point_id is not None
            }
        )
        rows: list[dict] = []
        for receipt, patient_name, collected_by_name in transactions:
            patient = patients.get(receipt.patient_id)
            pay_point = pay_points.get(receipt.cashier_pay_point_id) if receipt.cashier_pay_point_id else None
            rows.append(
                {
                    "receipt_id": receipt.id,
                    "receipt_number": receipt.receipt_number,
                    "visit_id": receipt.visit_id,
                    "patient_id": receipt.patient_id,
                    "patient_name": patient_name or (patient.get("full_name") if patient else None),
                    "patient_mrn": patient.get("mrn") if patient else None,
                    "amount_minor": int(receipt.total_amount_minor),
                    "currency": receipt.currency,
                    "payment_method": receipt.payment_method,
                    "cashier_pay_point_id": receipt.cashier_pay_point_id,
                    "cashier_pay_point_name": pay_point.name if pay_point else None,
                    "collected_by_name": collected_by_name,
                    "occurred_at": receipt.occurred_at,
                }
            )
        return rows

    def _build_exception_rows(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None,
        search: str | None,
        limit: int,
    ) -> list[dict]:
        query = (
            self.db.query(Prescription)
            .filter(
                Prescription.clinic_id == clinic_id,
                Prescription.exception_authorization_type
                != PharmacyExceptionAuthorizationType.NONE,
            )
            .order_by(Prescription.issued_at.desc())
        )
        if cashier_pay_point_id is not None:
            query = query.filter(
                Prescription.assigned_cashier_pay_point_id == cashier_pay_point_id
            )
        prescriptions = query.limit(limit * 3).all()
        if not prescriptions:
            return []

        visits = self._load_visits({row.visit_id for row in prescriptions})
        patients = self._load_patients(
            patient_ids={visit.patient_id for visit in visits.values()}
        )
        pay_points = self._load_pay_points(
            {
                row.assigned_cashier_pay_point_id
                for row in prescriptions
                if row.assigned_cashier_pay_point_id is not None
            }
        )
        units = self._load_service_lines(
            {
                row.assigned_dispensing_unit_id
                for row in prescriptions
                if row.assigned_dispensing_unit_id is not None
            }
        )
        billing_items = (
            {
                row.id: row
                for row in self.db.query(BillingItem)
                .filter(
                    BillingItem.id.in_(
                        [row.billing_item_id for row in prescriptions if row.billing_item_id is not None]
                    )
                )
                .all()
            }
            if any(row.billing_item_id is not None for row in prescriptions)
            else {}
        )

        rows: list[dict] = []
        for prescription in prescriptions:
            visit = visits.get(prescription.visit_id)
            patient = patients.get(visit.patient_id) if visit else None
            billing_item = billing_items.get(prescription.billing_item_id) if prescription.billing_item_id else None
            unit = units.get(prescription.assigned_dispensing_unit_id) if prescription.assigned_dispensing_unit_id else None
            pay_point = pay_points.get(prescription.assigned_cashier_pay_point_id) if prescription.assigned_cashier_pay_point_id else None
            row = {
                "prescription_id": prescription.id,
                "billing_item_id": prescription.billing_item_id,
                "patient_id": visit.patient_id if visit else None,
                "patient_name": patient.get("full_name") if patient else None,
                "patient_mrn": patient.get("mrn") if patient else None,
                "item_name": prescription.drug_name,
                "assigned_dispensing_unit_name": unit.name if unit else None,
                "exception_authorization_type": prescription.exception_authorization_type,
                "payment_status": "PAID" if billing_item and billing_item.status == BillingItemStatus.PAID else "UNPAID",
                "readiness_state": prescription.workflow_status,
                "cashier_pay_point_name": pay_point.name if pay_point else None,
                "occurred_at": prescription.exception_authorized_at or prescription.issued_at,
            }
            if self._matches_search(
                search,
                row["patient_name"],
                row["patient_mrn"],
                row["item_name"],
                row["assigned_dispensing_unit_name"],
                row["cashier_pay_point_name"],
                row["exception_authorization_type"],
            ):
                rows.append(row)
        return rows[:limit]

    def _build_activity_rows(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None,
        search: str | None,
        limit: int,
        receipt_rows: list[dict],
    ) -> list[dict]:
        activities: list[dict] = []

        for receipt in receipt_rows:
            activities.append(
                {
                    "id": f"payment:{receipt['receipt_id']}",
                    "action_type": "PAYMENT_PROCESSED",
                    "title": "Payment processed",
                    "detail": (
                        f"Receipt {receipt['receipt_number']} captured for {len(receipt['linked_items'])} billed item(s)."
                    ),
                    "patient_id": receipt["patient_id"],
                    "patient_name": receipt.get("patient_name"),
                    "patient_mrn": receipt.get("patient_mrn"),
                    "receipt_number": receipt["receipt_number"],
                    "occurred_at": receipt["occurred_at"],
                }
            )
            for hint in receipt.get("destination_hints", []):
                activities.append(
                    {
                        "id": f"unlock:{receipt['receipt_id']}:{hint}",
                        "action_type": "PHARMACY_UNLOCKED",
                        "title": "Pharmacy item unlocked",
                        "detail": hint,
                        "patient_id": receipt["patient_id"],
                        "patient_name": receipt.get("patient_name"),
                        "patient_mrn": receipt.get("patient_mrn"),
                        "receipt_number": receipt["receipt_number"],
                        "occurred_at": receipt["occurred_at"],
                    }
                )

        reprint_rows = self._load_reprint_logs(
            clinic_id=clinic_id,
            cashier_pay_point_id=cashier_pay_point_id,
            limit=10,
        )
        for log, receipt, patient_name, reprinted_by_name in reprint_rows:
            patient = self._load_patients(patient_ids={receipt.patient_id}).get(receipt.patient_id)
            activities.append(
                {
                    "id": f"reprint:{log.id}",
                    "action_type": "RECEIPT_REPRINTED",
                    "title": "Receipt reprinted",
                    "detail": f"Receipt {receipt.receipt_number} reprinted by {reprinted_by_name or 'Cashier' }.",
                    "patient_id": receipt.patient_id,
                    "patient_name": patient_name,
                    "patient_mrn": patient.get("mrn") if patient else None,
                    "receipt_number": receipt.receipt_number,
                    "occurred_at": log.reprinted_at,
                }
            )

        activities.sort(key=lambda row: row["occurred_at"], reverse=True)
        filtered = [
            row
            for row in activities
            if self._matches_search(
                search,
                row.get("patient_name"),
                row.get("patient_mrn"),
                row.get("title"),
                row.get("detail"),
                row.get("receipt_number"),
                row.get("action_type"),
            )
        ]
        return filtered[:limit]

    def _load_reprint_logs(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None,
        limit: int,
    ):
        query = (
            self.db.query(
                ReceiptReprintLog,
                PaymentReceipt,
                Patient.full_name.label("patient_name"),
                User.full_name.label("reprinted_by_name"),
            )
            .join(
                PaymentReceipt,
                (PaymentReceipt.id == ReceiptReprintLog.receipt_id)
                & (PaymentReceipt.clinic_id == ReceiptReprintLog.clinic_id),
            )
            .join(
                Patient,
                (Patient.id == PaymentReceipt.patient_id)
                & (Patient.clinic_id == PaymentReceipt.clinic_id),
            )
            .join(User, User.id == ReceiptReprintLog.reprinted_by)
            .filter(ReceiptReprintLog.clinic_id == clinic_id)
            .order_by(ReceiptReprintLog.reprinted_at.desc())
        )
        if cashier_pay_point_id is not None:
            query = query.filter(PaymentReceipt.cashier_pay_point_id == cashier_pay_point_id)
        return query.limit(limit).all()

    def _load_today_receipt_totals(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None,
        start: datetime,
        end: datetime,
    ) -> tuple[int, int]:
        query = self.db.query(
            func.count(PaymentReceipt.id),
            func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0),
        ).filter(
            PaymentReceipt.clinic_id == clinic_id,
            PaymentReceipt.occurred_at >= start,
            PaymentReceipt.occurred_at < end,
        )
        if cashier_pay_point_id is not None:
            query = query.filter(PaymentReceipt.cashier_pay_point_id == cashier_pay_point_id)
        row = query.first()
        return int(row[1] or 0), int(row[0] or 0)

    def _resolve_currency(
        self,
        *,
        clinic_id: UUID,
        charge_rows: list[dict],
        receipt_rows: list[dict],
    ) -> str:
        if charge_rows:
            return charge_rows[0]["currency"]
        if receipt_rows:
            return receipt_rows[0]["currency"]
        return (
            self.db.query(Clinic.billing_currency)
            .filter(Clinic.id == clinic_id)
            .scalar()
            or "NGN"
        )

    def _matches_search(self, search: str | None, *values) -> bool:
        if not search or not search.strip():
            return True
        term = search.strip().lower()
        return any(term in str(value).lower() for value in values if value is not None)
