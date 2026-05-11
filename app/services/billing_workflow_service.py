from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from app.models.billing_item import BillingItem
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.billing_refund import BillingRefund
from app.models.cashier_pay_point import CashierPayPoint
from app.models.cashier_shift import CashierShift
from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.lab_request import LabRequest
from app.models.lab_test_catalog import LabTestCatalog
from app.models.lab_test_config import LabTestConfig
from app.models.patient import Patient
from app.models.payment_receipt import PaymentReceipt
from app.models.payment_receipt_item import PaymentReceiptItem
from app.models.prescription import Prescription
from app.models.receipt_reprint_log import ReceiptReprintLog
from app.models.receipt_sequence import ReceiptSequence
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.event_service import EventService
from app.shared.enums import (
    BillingEntryType,
    BillingItemStatus,
    BillingReasonCode,
    LabRequestWorkflowStatus,
    UserRole,
)


class BillingWorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def list_charge_items(
        self,
        *,
        clinic_id: UUID,
        service_type: str | None = None,
        active_only: bool = True,
    ) -> list[ChargeCatalog | dict]:
        if service_type == "LAB_TEST":
            return self._list_lab_charge_items(
                clinic_id=clinic_id,
                active_only=active_only,
            )

        query = self.db.query(ChargeCatalog).filter(ChargeCatalog.clinic_id == clinic_id)
        if active_only:
            query = query.filter(ChargeCatalog.active.is_(True))

        return query.order_by(ChargeCatalog.category.asc(), ChargeCatalog.name.asc()).all()

    def resolve_lab_charge_item(
        self,
        *,
        clinic_id: UUID,
        test_name: str,
        test_code: str | None = None,
    ) -> ChargeCatalog:
        configured_query = self._configured_lab_charge_query(
            clinic_id=clinic_id,
            active_only=True,
        )
        if test_code:
            normalized_code = test_code.strip()
            configured_by_code = (
                configured_query
                .filter(LabTestCatalog.test_code == normalized_code)
                .first()
            )
            if configured_by_code is not None:
                charge_item, _, _, _ = configured_by_code
                return charge_item

            legacy_by_code = (
                self.db.query(ChargeCatalog)
                .filter(
                    ChargeCatalog.clinic_id == clinic_id,
                    ChargeCatalog.code == normalized_code,
                    ChargeCatalog.active.is_(True),
                )
                .first()
            )
            if legacy_by_code is not None:
                return legacy_by_code

        by_name = (
            configured_query
            .filter(
                func.lower(ChargeCatalog.name) == test_name.strip().lower(),
            )
            .first()
        )
        if by_name is not None:
            charge_item, _, _, _ = by_name
            return charge_item

        legacy_by_name = (
            self.db.query(ChargeCatalog)
            .filter(
                ChargeCatalog.clinic_id == clinic_id,
                func.lower(ChargeCatalog.name) == test_name.strip().lower(),
                ChargeCatalog.active.is_(True),
            )
            .first()
        )
        if legacy_by_name is not None:
            return legacy_by_name

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"No active lab price configured for '{test_name}'. "
                "Update the charge catalog before ordering this test."
            ),
        )

    def _configured_lab_charge_query(
        self,
        *,
        clinic_id: UUID,
        active_only: bool,
    ):
        query = (
            self.db.query(ChargeCatalog, LabTestCatalog, LabTestConfig, ServiceLine)
            .join(
                LabTestCatalog,
                (LabTestCatalog.clinic_id == ChargeCatalog.clinic_id)
                & (LabTestCatalog.test_code == ChargeCatalog.code),
            )
            .join(
                LabTestConfig,
                (LabTestConfig.clinic_id == LabTestCatalog.clinic_id)
                & (LabTestConfig.catalog_test_id == LabTestCatalog.id),
            )
            .join(
                ServiceLine,
                (ServiceLine.clinic_id == LabTestConfig.clinic_id)
                & (ServiceLine.id == LabTestConfig.unit_id),
            )
            .filter(
                ChargeCatalog.clinic_id == clinic_id,
                LabTestCatalog.clinic_id == clinic_id,
                LabTestConfig.clinic_id == clinic_id,
            )
        )
        if active_only:
            query = query.filter(
                ChargeCatalog.active.is_(True),
                LabTestCatalog.is_active.is_(True),
                LabTestConfig.is_enabled.is_(True),
                ServiceLine.is_active.is_(True),
            )
        return query

    def _list_lab_charge_items(
        self,
        *,
        clinic_id: UUID,
        active_only: bool,
    ) -> list[dict]:
        configured_rows = (
            self._configured_lab_charge_query(
                clinic_id=clinic_id,
                active_only=active_only,
            )
            .order_by(
                ServiceLine.name.asc(),
                LabTestConfig.display_order.asc(),
                ChargeCatalog.name.asc(),
            )
            .all()
        )
        if configured_rows:
            return [
                {
                    "id": charge_item.id,
                    "code": catalog.test_code,
                    "name": config.billing_name,
                    "category": unit.name,
                    "default_amount_minor": config.price_minor,
                    "currency": config.currency,
                    "active": bool(charge_item.active and config.is_enabled and catalog.is_active),
                    "display_order": config.display_order,
                    "unit_id": unit.id,
                    "unit_name": unit.name,
                }
                for charge_item, catalog, config, unit in configured_rows
            ]

        legacy_query = self.db.query(ChargeCatalog).filter(
            ChargeCatalog.clinic_id == clinic_id,
        )
        if active_only:
            legacy_query = legacy_query.filter(ChargeCatalog.active.is_(True))
        legacy_rows = legacy_query.filter(ChargeCatalog.code.like("LAB_%")).order_by(
            ChargeCatalog.category.asc(),
            ChargeCatalog.name.asc(),
        )
        return [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "category": item.category,
                "default_amount_minor": item.default_amount_minor,
                "currency": item.currency,
                "active": item.active,
                "display_order": None,
                "unit_id": None,
                "unit_name": None,
            }
            for item in legacy_rows.all()
        ]

    def create_lab_billing_item(
        self,
        *,
        visit: Visit,
        test_name: str,
        test_code: str | None,
        actor,
        auto_commit: bool = True,
    ) -> BillingItem:
        charge_item = self.resolve_lab_charge_item(
            clinic_id=visit.clinic_id,
            test_name=test_name,
            test_code=test_code,
        )

        billing_item = BillingItem(
            id=uuid.uuid4(),
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            visit_id=visit.id,
            charge_catalog_id=charge_item.id,
            charge_code=charge_item.code,
            item_name=charge_item.name,
            service_type="LAB_TEST",
            quantity=1,
            unit_price_minor=charge_item.default_amount_minor,
            total_minor=charge_item.default_amount_minor,
            amount_paid_minor=0,
            currency=charge_item.currency,
            status=BillingItemStatus.PENDING,
            created_by=actor.id,
            payment_reference=None,
            paid_at=None,
        )
        self.db.add(billing_item)

        self.db.add(
            BillingLedgerEntry(
                clinic_id=visit.clinic_id,
                patient_id=visit.patient_id,
                visit_id=visit.id,
                admission_id=None,
                entry_type=BillingEntryType.CHARGE,
                amount_minor=charge_item.default_amount_minor,
                currency=charge_item.currency,
                description=f"Lab Test: {charge_item.name}",
                reason_code=BillingReasonCode.LAB_TEST,
                charge_code=charge_item.code,
                external_ref=None,
                related_entry_id=None,
                actor_id=actor.id,
                actor_role=actor.role,
                occurred_at=datetime.now(timezone.utc),
            )
        )

        if auto_commit:
            self.db.commit()
            self.db.refresh(billing_item)

        return billing_item

    def list_pending_visit_summaries(
        self,
        *,
        clinic_id: UUID,
        cashier_pay_point_id: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        query = (
            self.db.query(
                BillingItem.visit_id.label("visit_id"),
                BillingItem.patient_id.label("patient_id"),
                Patient.full_name.label("patient_name"),
                BillingItem.currency.label("currency"),
                func.count(BillingItem.id).label("pending_items_count"),
                func.coalesce(func.sum(BillingItem.total_minor), 0).label("pending_total_minor"),
                func.max(BillingItem.created_at).label("latest_created_at"),
            )
            .join(
                Patient,
                (Patient.id == BillingItem.patient_id)
                & (Patient.clinic_id == BillingItem.clinic_id),
            )
            .filter(
                BillingItem.clinic_id == clinic_id,
                BillingItem.status == BillingItemStatus.PENDING,
            )
        )

        if cashier_pay_point_id is not None:
            query = query.filter(
                (BillingItem.cashier_pay_point_id == cashier_pay_point_id)
                | (BillingItem.cashier_pay_point_id.is_(None))
            )

        if search:
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Patient.full_name).like(term))
                | (cast(BillingItem.visit_id, String).like(term))
            )

        rows = (
            query.group_by(
                BillingItem.visit_id,
                BillingItem.patient_id,
                Patient.full_name,
                BillingItem.currency,
            )
            .order_by(func.max(BillingItem.created_at).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "visit_id": row.visit_id,
                "patient_id": row.patient_id,
                "patient_name": row.patient_name,
                "currency": row.currency,
                "pending_items_count": int(row.pending_items_count or 0),
                "pending_total_minor": int(row.pending_total_minor or 0),
                "latest_created_at": row.latest_created_at,
            }
            for row in rows
        ]

    def list_visit_items(
        self,
        *,
        clinic_id: UUID,
        visit_id: UUID,
    ) -> list[BillingItem]:
        return (
            self.db.query(BillingItem)
            .filter(
                BillingItem.clinic_id == clinic_id,
                BillingItem.visit_id == visit_id,
            )
            .order_by(BillingItem.created_at.asc())
            .all()
        )

    def pay_billing_items(
        self,
        *,
        clinic_id: UUID,
        visit_id: UUID,
        billing_item_ids: list[UUID],
        cashier_pay_point_id: UUID | None = None,
        payment_method: BillingReasonCode,
        cashier_user,
        external_ref: str | None = None,
        notes: str | None = None,
    ) -> dict:
        if payment_method not in {
            BillingReasonCode.CASH,
            BillingReasonCode.TRANSFER,
            BillingReasonCode.CARD,
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Payment method must be CASH, TRANSFER, or CARD",
            )

        if payment_method in {BillingReasonCode.TRANSFER, BillingReasonCode.CARD}:
            if external_ref is None or len(external_ref.strip()) < 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Payment reference is required for transfer/card",
                )

        if not billing_item_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="At least one billing item must be provided",
            )

        actor_role = getattr(cashier_user.role, "value", cashier_user.role)
        if actor_role == UserRole.CASHIER.value:
            has_open_shift = (
                self.db.query(CashierShift.id)
                .filter(
                    CashierShift.clinic_id == clinic_id,
                    CashierShift.cashier_id == cashier_user.id,
                    CashierShift.status == "OPEN",
                )
                .first()
            )
            if has_open_shift is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Start an active cashier shift before collecting payment",
                )

        locked_items = (
            self.db.query(BillingItem)
            .filter(
                BillingItem.clinic_id == clinic_id,
                BillingItem.visit_id == visit_id,
                BillingItem.id.in_(billing_item_ids),
            )
            .with_for_update()
            .all()
        )

        if len(locked_items) != len(set(billing_item_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more billing items were not found for this visit",
            )

        pending_items = [item for item in locked_items if item.status == BillingItemStatus.PENDING]
        if len(pending_items) != len(locked_items):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="One or more billing items are no longer pending",
            )

        patient_ids = {item.patient_id for item in pending_items}
        if len(patient_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Billing items must belong to a single patient",
            )
        patient_id = pending_items[0].patient_id
        currency = pending_items[0].currency
        if any(item.currency != currency for item in pending_items):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot pay billing items with mixed currencies",
            )

        total_minor = sum(item.total_minor - item.amount_paid_minor for item in pending_items)
        if total_minor <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Billing items are already settled",
            )

        resolved_pay_point_id: UUID | None = cashier_pay_point_id
        if getattr(cashier_user.role, "value", cashier_user.role) == UserRole.CASHIER.value:
            resolved_pay_point = CashierPayPointAccessService(self.db).resolve_selected_pay_point(
                clinic_id=clinic_id,
                user=cashier_user,
                selected_pay_point_id=cashier_pay_point_id,
            )
            resolved_pay_point_id = resolved_pay_point.id

        item_pay_point_ids = {
            item.cashier_pay_point_id
            for item in pending_items
            if item.cashier_pay_point_id is not None
        }
        if resolved_pay_point_id is not None and item_pay_point_ids and item_pay_point_ids != {resolved_pay_point_id}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected billing items belong to a different cashier pay point",
            )

        paid_at = datetime.now(timezone.utc)
        receipt_number = self._generate_receipt_number(clinic_id=clinic_id)
        receipt = PaymentReceipt(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patient_id,
            visit_id=visit_id,
            cashier_pay_point_id=resolved_pay_point_id,
            receipt_number=receipt_number,
            total_amount_minor=total_minor,
            currency=currency,
            payment_method=payment_method,
            external_ref=external_ref.strip() if external_ref else None,
            notes=notes.strip() if notes else None,
            collected_by=cashier_user.id,
            occurred_at=paid_at,
        )
        self.db.add(receipt)

        for item in pending_items:
            outstanding = item.total_minor - item.amount_paid_minor
            self.db.add(
                PaymentReceiptItem(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    receipt_id=receipt.id,
                    billing_item_id=item.id,
                    amount_minor=outstanding,
                )
            )
            item.amount_paid_minor = item.total_minor
            item.status = BillingItemStatus.PAID
            item.paid_at = paid_at
            item.payment_reference = receipt_number
            self.db.add(item)

        paid_item_ids = {item.id for item in pending_items}
        destination_hints: list[dict] = []
        if paid_item_ids:
            lab_requests = (
                self.db.query(LabRequest)
                .filter(LabRequest.billing_item_id.in_(paid_item_ids))
                .all()
            )
            from app.services.lab_foundation_service import LabFoundationService
            from app.services.pharmacy_service import PharmacyService

            foundation_service = LabFoundationService(self.db)
            pharmacy_service = PharmacyService(self.db)
            for lab_request in lab_requests:
                foundation_service.reconcile_request_configuration(
                    lab_request=lab_request,
                    auto_commit=False,
                )
                if lab_request.workflow_status == LabRequestWorkflowStatus.ORDERED:
                    lab_request.workflow_status = LabRequestWorkflowStatus.PAID
                    self.db.add(lab_request)
            pharmacy_service.mark_prescriptions_paid(billing_item_ids=paid_item_ids)
            pharmacy_prescriptions = (
                self.db.query(Prescription)
                .filter(Prescription.billing_item_id.in_(paid_item_ids))
                .all()
            )
            unit_map = {
                row.id: row
                for row in self.db.query(ServiceLine)
                .filter(
                    ServiceLine.id.in_(
                        [
                            prescription.assigned_dispensing_unit_id
                            for prescription in pharmacy_prescriptions
                            if prescription.assigned_dispensing_unit_id is not None
                        ]
                    )
                )
                .all()
            }
            for item in pending_items:
                matching = next(
                    (
                        prescription
                        for prescription in pharmacy_prescriptions
                        if prescription.billing_item_id == item.id
                    ),
                    None,
                )
                if matching is None:
                    continue
                unit = (
                    unit_map.get(matching.assigned_dispensing_unit_id)
                    if matching.assigned_dispensing_unit_id is not None
                    else None
                )
                destination_hints.append(
                    {
                        "billing_item_id": item.id,
                        "item_name": item.item_name,
                        "service_type": item.service_type,
                        "destination_label": (
                            f"Ready for Pharmacy Dispense — {unit.name}"
                            if unit is not None
                            else "Ready for Pharmacy Dispense"
                        ),
                        "assigned_dispensing_unit_id": matching.assigned_dispensing_unit_id,
                        "assigned_dispensing_unit_name": unit.name if unit is not None else None,
                        "readiness_state": matching.workflow_status.value,
                    }
                )
            if pharmacy_prescriptions:
                event_service = EventService(self.db)
                event_service.build_event(
                    event_type="PHARMACY_PAYMENT_CAPTURED",
                    actor_id=cashier_user.id,
                    actor_role=getattr(cashier_user.role, "value", cashier_user.role),
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    emitter="billing_workflow_service",
                    payload={
                        "visit_id": str(visit_id),
                        "receipt_id": str(receipt.id),
                        "receipt_number": receipt_number,
                        "cashier_pay_point_id": (
                            str(resolved_pay_point_id)
                            if resolved_pay_point_id is not None
                            else None
                        ),
                        "paid_item_ids": [str(item.id) for item in pending_items],
                    },
                )
                event_service.build_event(
                    event_type="PHARMACY_RECEIPT_CREATED",
                    actor_id=cashier_user.id,
                    actor_role=getattr(cashier_user.role, "value", cashier_user.role),
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    emitter="billing_workflow_service",
                    payload={
                        "visit_id": str(visit_id),
                        "receipt_id": str(receipt.id),
                        "receipt_number": receipt_number,
                        "total_paid_minor": int(total_minor),
                        "currency": currency,
                    },
                )
                for prescription in pharmacy_prescriptions:
                    event_service.build_event(
                        event_type="PHARMACY_ITEM_READY_FOR_DISPENSE",
                        actor_id=cashier_user.id,
                        actor_role=getattr(cashier_user.role, "value", cashier_user.role),
                        clinic_id=clinic_id,
                        patient_id=patient_id,
                        emitter="billing_workflow_service",
                        payload={
                            "billing_item_id": (
                                str(prescription.billing_item_id)
                                if prescription.billing_item_id is not None
                                else None
                            ),
                            "prescription_id": str(prescription.id),
                            "assigned_dispensing_unit_id": (
                                str(prescription.assigned_dispensing_unit_id)
                                if prescription.assigned_dispensing_unit_id is not None
                                else None
                            ),
                            "readiness_state": prescription.workflow_status.value,
                            "receipt_number": receipt_number,
                        },
                    )

        ledger_external_ref = external_ref.strip() if external_ref else receipt_number
        self.db.add(
            BillingLedgerEntry(
                clinic_id=clinic_id,
                patient_id=patient_id,
                visit_id=visit_id,
                admission_id=None,
                entry_type=BillingEntryType.PAYMENT,
                amount_minor=-abs(total_minor),
                currency=currency,
                description=(notes.strip() if notes else f"Lab payment receipt {receipt_number}"),
                reason_code=payment_method,
                charge_code=None,
                external_ref=ledger_external_ref,
                related_entry_id=None,
                actor_id=cashier_user.id,
                actor_role=cashier_user.role,
                occurred_at=paid_at,
            )
        )

        self.db.commit()

        return {
            "receipt_number": receipt_number,
            "receipt_id": receipt.id,
            "visit_id": visit_id,
            "patient_id": patient_id,
            "cashier_pay_point_id": resolved_pay_point_id,
            "total_paid_minor": total_minor,
            "currency": currency,
            "payment_method": payment_method,
            "paid_item_ids": [item.id for item in pending_items],
            "paid_at": paid_at,
            "destination_hints": destination_hints,
        }

    def list_receipts(
        self,
        *,
        clinic_id: UUID,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 200,
    ) -> list[dict]:
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

        if date_from is not None:
            from_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
            query = query.filter(PaymentReceipt.occurred_at >= from_dt)
        if date_to is not None:
            to_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
            query = query.filter(PaymentReceipt.occurred_at < to_dt)

        if search:
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Patient.full_name).like(term))
                | (func.lower(PaymentReceipt.receipt_number).like(term))
                | (cast(PaymentReceipt.visit_id, String).like(term))
            )

        rows = (
            query.order_by(PaymentReceipt.occurred_at.desc())
            .limit(limit)
            .all()
        )

        result: list[dict] = []
        for receipt, patient_name, collected_by_name in rows:
            result.append(
                {
                    "id": receipt.id,
                    "clinic_id": receipt.clinic_id,
                    "patient_id": receipt.patient_id,
                    "patient_name": patient_name,
                    "visit_id": receipt.visit_id,
                    "cashier_pay_point_id": receipt.cashier_pay_point_id,
                    "receipt_number": receipt.receipt_number,
                    "total_amount_minor": receipt.total_amount_minor,
                    "currency": receipt.currency,
                    "payment_method": receipt.payment_method,
                    "external_ref": receipt.external_ref,
                    "collected_by": receipt.collected_by,
                    "collected_by_name": collected_by_name,
                    "occurred_at": receipt.occurred_at,
                }
            )
        return result

    def list_transactions(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        payment_method: BillingReasonCode | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 25,
    ) -> dict:
        if payment_method is not None and payment_method not in {
            BillingReasonCode.CASH,
            BillingReasonCode.CARD,
            BillingReasonCode.TRANSFER,
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Payment method filter must be CASH, CARD, or TRANSFER",
            )

        if start_date is not None and end_date is not None and end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="end_date cannot be before start_date",
            )

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

        if start_date is not None:
            start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            query = query.filter(PaymentReceipt.occurred_at >= start_dt)
        if end_date is not None:
            end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
            query = query.filter(PaymentReceipt.occurred_at < end_dt)
        if payment_method is not None:
            query = query.filter(PaymentReceipt.payment_method == payment_method)
        if search:
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Patient.full_name).like(term))
                | (func.lower(PaymentReceipt.receipt_number).like(term))
                | (cast(PaymentReceipt.visit_id, String).like(term))
            )

        total = int(query.with_entities(func.count(PaymentReceipt.id)).order_by(None).scalar() or 0)
        total_amount_minor = int(
            query.with_entities(func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0))
            .order_by(None)
            .scalar()
            or 0
        )

        rows = (
            query.order_by(PaymentReceipt.occurred_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        currency = (
            rows[0][0].currency
            if rows
            else (
                self.db.query(Clinic.billing_currency)
                .filter(Clinic.id == clinic_id)
                .scalar()
                or "NGN"
            )
        )

        return {
            "data": [
                {
                    "receipt_id": receipt.id,
                    "receipt_number": receipt.receipt_number,
                    "occurred_at": receipt.occurred_at,
                    "patient_name": patient_name,
                    "visit_id": receipt.visit_id,
                    "amount_minor": int(receipt.total_amount_minor),
                    "currency": receipt.currency,
                    "payment_method": receipt.payment_method,
                    "collected_by_name": collected_by_name,
                }
                for receipt, patient_name, collected_by_name in rows
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "total_amount_minor": total_amount_minor,
            "currency": currency,
        }

    def get_receipt_detail(self, *, clinic_id: UUID, receipt_id: UUID) -> dict:
        row = (
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
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.id == receipt_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

        receipt, patient_name, collected_by_name = row

        item_rows = (
            self.db.query(
                PaymentReceiptItem,
                BillingItem.item_name.label("item_name"),
                BillingItem.charge_code.label("charge_code"),
            )
            .join(
                BillingItem,
                (BillingItem.id == PaymentReceiptItem.billing_item_id)
                & (BillingItem.clinic_id == PaymentReceiptItem.clinic_id),
            )
            .filter(
                PaymentReceiptItem.clinic_id == clinic_id,
                PaymentReceiptItem.receipt_id == receipt.id,
            )
            .order_by(PaymentReceiptItem.created_at.asc())
            .all()
        )

        return {
            "id": receipt.id,
            "clinic_id": receipt.clinic_id,
            "patient_id": receipt.patient_id,
            "patient_name": patient_name,
            "visit_id": receipt.visit_id,
            "cashier_pay_point_id": receipt.cashier_pay_point_id,
            "receipt_number": receipt.receipt_number,
            "total_amount_minor": receipt.total_amount_minor,
            "currency": receipt.currency,
            "payment_method": receipt.payment_method,
            "external_ref": receipt.external_ref,
            "notes": receipt.notes,
            "collected_by": receipt.collected_by,
            "collected_by_name": collected_by_name,
            "occurred_at": receipt.occurred_at,
            "items": [
                {
                    "id": alloc.id,
                    "billing_item_id": alloc.billing_item_id,
                    "amount_minor": alloc.amount_minor,
                    "item_name": item_name,
                    "charge_code": charge_code,
                }
                for alloc, item_name, charge_code in item_rows
            ],
        }

    def log_receipt_reprint(self, *, clinic_id: UUID, receipt_id: UUID, actor, reason: str | None = None) -> dict:
        receipt = (
            self.db.query(PaymentReceipt)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.id == receipt_id,
            )
            .first()
        )
        if receipt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

        log = ReceiptReprintLog(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            receipt_id=receipt_id,
            reprinted_by=actor.id,
            reason=reason.strip() if reason else None,
            reprinted_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.commit()

        return {
            "receipt_id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "reprint_log_id": log.id,
            "reprinted_at": log.reprinted_at,
        }

    def get_receipt_sequence(self, *, clinic_id: UUID) -> ReceiptSequence:
        sequence = (
            self.db.query(ReceiptSequence)
            .filter(ReceiptSequence.clinic_id == clinic_id)
            .first()
        )
        if sequence is None:
            sequence = ReceiptSequence(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                prefix="RCPT",
                padding=6,
                last_number=0,
                reset_yearly=False,
                current_year=datetime.now(timezone.utc).year,
            )
            self.db.add(sequence)
            self.db.commit()
            self.db.refresh(sequence)
        return sequence

    def update_receipt_sequence(
        self,
        *,
        clinic_id: UUID,
        prefix: str,
        padding: int,
        reset_yearly: bool,
    ) -> ReceiptSequence:
        sequence = self.get_receipt_sequence(clinic_id=clinic_id)
        sequence.prefix = prefix.strip().upper()
        sequence.padding = padding
        sequence.reset_yearly = reset_yearly
        if sequence.current_year is None:
            sequence.current_year = datetime.now(timezone.utc).year
        self.db.add(sequence)
        self.db.commit()
        self.db.refresh(sequence)
        return sequence

    def process_refund(
        self,
        *,
        clinic_id: UUID,
        receipt_id: UUID,
        actor,
        reason: str,
        amount_minor: int | None = None,
        billing_item_id: UUID | None = None,
        notes: str | None = None,
    ) -> dict:
        receipt = (
            self.db.query(PaymentReceipt)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.id == receipt_id,
            )
            .with_for_update()
            .first()
        )
        if receipt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

        alloc_rows = (
            self.db.query(PaymentReceiptItem, BillingItem)
            .join(
                BillingItem,
                (BillingItem.id == PaymentReceiptItem.billing_item_id)
                & (BillingItem.clinic_id == PaymentReceiptItem.clinic_id),
            )
            .filter(
                PaymentReceiptItem.clinic_id == clinic_id,
                PaymentReceiptItem.receipt_id == receipt.id,
            )
            .with_for_update()
            .all()
        )

        if billing_item_id is not None:
            alloc_rows = [row for row in alloc_rows if row[0].billing_item_id == billing_item_id]

        if not alloc_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No refundable billing items found for receipt",
            )

        total_refundable = sum(item.amount_paid_minor for _alloc, item in alloc_rows)
        if total_refundable <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected items have no refundable balance",
            )

        refund_total = amount_minor if amount_minor is not None else total_refundable
        if refund_total <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Refund amount must be positive",
            )
        if refund_total > total_refundable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Refund amount exceeds refundable balance",
            )

        remaining = refund_total
        refunded_item_ids: list[UUID] = []
        refund_record_ids: list[UUID] = []
        now = datetime.now(timezone.utc)

        for _alloc, item in alloc_rows:
            if remaining <= 0:
                break
            available = item.amount_paid_minor
            if available <= 0:
                continue
            portion = min(available, remaining)
            item.amount_paid_minor -= portion

            if item.amount_paid_minor <= 0:
                item.amount_paid_minor = 0
                item.status = BillingItemStatus.REFUNDED
                item.paid_at = None
            elif item.amount_paid_minor < item.total_minor:
                item.status = BillingItemStatus.PENDING
                item.paid_at = None

            self.db.add(item)
            refunded_item_ids.append(item.id)

            refund_record = BillingRefund(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                receipt_id=receipt.id,
                billing_item_id=item.id,
                amount_minor=portion,
                currency=item.currency,
                reason=reason.strip(),
                status="PROCESSED",
                requested_by=actor.id,
                approved_by=actor.id,
                processed_by=actor.id,
                requested_at=now,
                processed_at=now,
                notes=notes.strip() if notes else None,
            )
            self.db.add(refund_record)
            refund_record_ids.append(refund_record.id)

            remaining -= portion

        if remaining != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to allocate full refund amount",
            )

        self.db.add(
            BillingLedgerEntry(
                clinic_id=clinic_id,
                patient_id=receipt.patient_id,
                visit_id=receipt.visit_id,
                admission_id=None,
                entry_type=BillingEntryType.REFUND,
                amount_minor=abs(refund_total),
                currency=receipt.currency,
                description=f"Refund for {receipt.receipt_number}: {reason.strip()}",
                reason_code=BillingReasonCode.REFUND,
                charge_code=None,
                external_ref=f"RFND-{receipt.receipt_number}",
                related_entry_id=None,
                actor_id=actor.id,
                actor_role=actor.role,
                occurred_at=now,
            )
        )

        self.db.commit()

        return {
            "refund_id": refund_record_ids[0],
            "receipt_id": receipt.id,
            "amount_minor": refund_total,
            "currency": receipt.currency,
            "status": "PROCESSED",
            "processed_at": now,
            "refunded_item_ids": refunded_item_ids,
        }

    def get_daily_report(self, *, clinic_id: UUID, for_date: date) -> dict:
        start_dt = datetime.combine(for_date, time.min, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        receipts = (
            self.db.query(PaymentReceipt)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= start_dt,
                PaymentReceipt.occurred_at < end_dt,
            )
            .all()
        )

        total_collected_minor = sum(r.total_amount_minor for r in receipts)
        receipts_count = len(receipts)
        currency = receipts[0].currency if receipts else (
            self.db.query(Clinic.billing_currency)
            .filter(Clinic.id == clinic_id)
            .scalar()
            or "NGN"
        )

        method_rows = (
            self.db.query(
                PaymentReceipt.payment_method,
                func.count(PaymentReceipt.id),
                func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0),
            )
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= start_dt,
                PaymentReceipt.occurred_at < end_dt,
            )
            .group_by(PaymentReceipt.payment_method)
            .all()
        )

        refund_rows = (
            self.db.query(
                func.count(BillingRefund.id),
                func.coalesce(func.sum(BillingRefund.amount_minor), 0),
            )
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.status == "PROCESSED",
                BillingRefund.processed_at >= start_dt,
                BillingRefund.processed_at < end_dt,
            )
            .first()
        )
        refunds_count = int(refund_rows[0] or 0)
        total_refunded_minor = int(refund_rows[1] or 0)

        return {
            "date": for_date.isoformat(),
            "clinic_id": clinic_id,
            "total_collected_minor": int(total_collected_minor),
            "total_refunded_minor": total_refunded_minor,
            "net_collected_minor": int(total_collected_minor - total_refunded_minor),
            "currency": currency,
            "receipts_count": receipts_count,
            "refunds_count": refunds_count,
            "method_breakdown": [
                {
                    "payment_method": row[0],
                    "count": int(row[1] or 0),
                    "total_minor": int(row[2] or 0),
                }
                for row in method_rows
            ],
        }

    def start_shift(self, *, clinic_id: UUID, cashier_user, opening_float_minor: int = 0) -> CashierShift:
        existing = (
            self.db.query(CashierShift)
            .filter(
                CashierShift.clinic_id == clinic_id,
                CashierShift.cashier_id == cashier_user.id,
                CashierShift.status == "OPEN",
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active shift already exists")

        shift = CashierShift(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            cashier_id=cashier_user.id,
            status="OPEN",
            started_at=datetime.now(timezone.utc),
            opening_float_minor=opening_float_minor,
        )
        self.db.add(shift)
        self.db.commit()
        self.db.refresh(shift)
        return shift

    def get_current_shift(self, *, clinic_id: UUID, cashier_user) -> CashierShift | None:
        return (
            self.db.query(CashierShift)
            .filter(
                CashierShift.clinic_id == clinic_id,
                CashierShift.cashier_id == cashier_user.id,
                CashierShift.status == "OPEN",
            )
            .order_by(CashierShift.started_at.desc())
            .first()
        )

    def end_shift(
        self,
        *,
        clinic_id: UUID,
        cashier_user,
        closing_cash_minor: int | None = None,
        closing_note: str | None = None,
    ) -> CashierShift:
        shift = self.get_current_shift(clinic_id=clinic_id, cashier_user=cashier_user)
        if shift is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active shift")

        shift.status = "CLOSED"
        shift.ended_at = datetime.now(timezone.utc)
        shift.closing_cash_minor = closing_cash_minor
        shift.closing_note = closing_note.strip() if closing_note else None

        self.db.add(shift)
        self.db.commit()
        self.db.refresh(shift)
        return shift

    def get_shift_report(self, *, clinic_id: UUID, shift_id: UUID, requester) -> dict:
        shift = (
            self.db.query(CashierShift)
            .filter(
                CashierShift.clinic_id == clinic_id,
                CashierShift.id == shift_id,
            )
            .first()
        )
        if shift is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

        requester_role = getattr(requester.role, "value", requester.role)
        if requester_role == "CASHIER" and shift.cashier_id != requester.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Shift access denied")

        end_dt = shift.ended_at or datetime.now(timezone.utc)

        receipts = (
            self.db.query(PaymentReceipt)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.collected_by == shift.cashier_id,
                PaymentReceipt.occurred_at >= shift.started_at,
                PaymentReceipt.occurred_at <= end_dt,
            )
            .all()
        )

        method_rows = (
            self.db.query(
                PaymentReceipt.payment_method,
                func.count(PaymentReceipt.id),
                func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0),
            )
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.collected_by == shift.cashier_id,
                PaymentReceipt.occurred_at >= shift.started_at,
                PaymentReceipt.occurred_at <= end_dt,
            )
            .group_by(PaymentReceipt.payment_method)
            .all()
        )

        refunds = (
            self.db.query(
                func.count(BillingRefund.id),
                func.coalesce(func.sum(BillingRefund.amount_minor), 0),
            )
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.processed_by == shift.cashier_id,
                BillingRefund.status == "PROCESSED",
                BillingRefund.processed_at >= shift.started_at,
                BillingRefund.processed_at <= end_dt,
            )
            .first()
        )

        total_collected_minor = int(sum(r.total_amount_minor for r in receipts))
        total_refunded_minor = int(refunds[1] or 0)

        return {
            "shift": shift,
            "total_collected_minor": total_collected_minor,
            "total_refunded_minor": total_refunded_minor,
            "net_collected_minor": total_collected_minor - total_refunded_minor,
            "receipts_count": len(receipts),
            "refunds_count": int(refunds[0] or 0),
            "method_breakdown": [
                {
                    "payment_method": row[0],
                    "count": int(row[1] or 0),
                    "total_minor": int(row[2] or 0),
                }
                for row in method_rows
            ],
        }

    def is_lab_request_paid(self, *, lab_request: LabRequest) -> bool:
        if lab_request.billing_item_id is None:
            return False
        item = (
            self.db.query(BillingItem.status)
            .filter(BillingItem.id == lab_request.billing_item_id)
            .first()
        )
        return bool(item and item.status == BillingItemStatus.PAID)

    def attach_lab_request_billing(self, *, lab_requests: list[LabRequest]) -> None:
        if not lab_requests:
            return
        item_ids = {req.billing_item_id for req in lab_requests if req.billing_item_id is not None}
        if not item_ids:
            for req in lab_requests:
                req.billing_status = "UNPAID"
                req.billing_total_minor = None
                req.billing_currency = None
                req.payment_verified = False
            return

        rows = self.db.query(BillingItem).filter(BillingItem.id.in_(item_ids)).all()
        item_map = {item.id: item for item in rows}
        for req in lab_requests:
            item = item_map.get(req.billing_item_id) if req.billing_item_id else None
            if item is None:
                req.billing_status = "UNPAID"
                req.billing_total_minor = None
                req.billing_currency = None
                req.payment_verified = False
                continue
            req.billing_status = item.status.value
            req.billing_total_minor = item.total_minor
            req.billing_currency = item.currency
            req.payment_verified = item.status == BillingItemStatus.PAID

    def _generate_receipt_number(self, *, clinic_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        year = now.year

        sequence = (
            self.db.query(ReceiptSequence)
            .filter(ReceiptSequence.clinic_id == clinic_id)
            .with_for_update()
            .first()
        )
        if sequence is None:
            sequence = ReceiptSequence(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                prefix="RCPT",
                padding=6,
                last_number=0,
                reset_yearly=False,
                current_year=year,
            )
            self.db.add(sequence)
            self.db.flush()

        if sequence.reset_yearly:
            if sequence.current_year != year:
                sequence.current_year = year
                sequence.last_number = 0
            sequence.last_number += 1
            serial = str(sequence.last_number).zfill(sequence.padding)
            receipt_number = f"{sequence.prefix}-{year}-{serial}"
        else:
            if sequence.current_year is None:
                sequence.current_year = year
            sequence.last_number += 1
            serial = str(sequence.last_number).zfill(sequence.padding)
            receipt_number = f"{sequence.prefix}-{serial}"

        self.db.add(sequence)
        return receipt_number
