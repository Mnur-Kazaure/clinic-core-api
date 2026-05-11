from __future__ import annotations

import csv
import hashlib
import json
import uuid
from datetime import date, datetime, time, timedelta, timezone
from io import StringIO
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, literal
from sqlalchemy.orm import Session, aliased

from app.models.billing_item import BillingItem
from app.models.billing_refund import BillingRefund
from app.models.cashier_shift import CashierShift
from app.models.clinic import Clinic
from app.models.department import Department
from app.models.idempotency import IdempotencyKey
from app.models.patient import Patient
from app.models.payment_receipt import PaymentReceipt
from app.models.receipt_reprint_log import ReceiptReprintLog
from app.models.refund_reason import RefundReason
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.shared.enums import BillingItemStatus, BillingReasonCode


class AccountantService:
    LARGE_REFUND_THRESHOLD_MINOR = 5_000_000  # NGN 50,000 (minor units)
    VARIANCE_THRESHOLD_MINOR = 10_000  # NGN 100
    HIGH_CASH_THRESHOLD_MINOR = 10_000_000  # NGN 100,000
    DEFAULT_REFUND_REASONS = [
        ("DUPLICATE", "Duplicate payment"),
        ("WRONG_CHARGE", "Wrong charge"),
        ("SERVICE_NOT_RENDERED", "Service not rendered"),
        ("INSURANCE_ADJUSTMENT", "Insurance adjustment"),
    ]

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _hash_request(payload: dict) -> str:
        normalized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def _day_bounds(target_date: date) -> tuple[datetime, datetime]:
        start_dt = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)
        return start_dt, end_dt

    def _range_bounds(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[datetime, datetime, date, date]:
        resolved_start = start_date or end_date or datetime.now(timezone.utc).date()
        resolved_end = end_date or start_date or resolved_start
        if resolved_end < resolved_start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="end_date cannot be before start_date",
            )
        start_dt = datetime.combine(resolved_start, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(
            resolved_end + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        return start_dt, end_dt, resolved_start, resolved_end

    def _resolve_currency(self, *, clinic_id: UUID) -> str:
        return (
            self.db.query(Clinic.billing_currency)
            .filter(Clinic.id == clinic_id)
            .scalar()
            or "NGN"
        )

    def _expected_shift_total_minor(self, *, clinic_id: UUID, shift: CashierShift) -> int:
        end_dt = shift.ended_at or datetime.now(timezone.utc)
        return int(
            self.db.query(func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0))
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.collected_by == shift.cashier_id,
                PaymentReceipt.occurred_at >= shift.started_at,
                PaymentReceipt.occurred_at <= end_dt,
            )
            .scalar()
            or 0
        )

    def _apply_department_scope(
        self,
        *,
        query,
        billing_item_entity,
        department_id: UUID | None,
    ):
        if department_id is None:
            return query

        leaf_sl = aliased(ServiceLine)
        root_sl = aliased(ServiceLine)

        return (
            query.join(
                Visit,
                and_(
                    Visit.id == billing_item_entity.visit_id,
                    Visit.clinic_id == billing_item_entity.clinic_id,
                ),
            )
            .outerjoin(
                leaf_sl,
                and_(
                    leaf_sl.id == Visit.service_line_id,
                    leaf_sl.clinic_id == Visit.clinic_id,
                ),
            )
            .outerjoin(
                root_sl,
                and_(
                    root_sl.id == leaf_sl.parent_id,
                    root_sl.clinic_id == leaf_sl.clinic_id,
                ),
            )
            .filter(func.coalesce(leaf_sl.department_id, root_sl.department_id) == department_id)
        )

    def get_overview(
        self,
        *,
        clinic_id: UUID,
        for_date: date,
    ) -> dict:
        day_start, day_end = self._day_bounds(for_date)
        month_start = for_date.replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        month_start_dt = datetime.combine(month_start, time.min, tzinfo=timezone.utc)
        month_end_dt = datetime.combine(next_month, time.min, tzinfo=timezone.utc)

        revenue_today_minor = int(
            self.db.query(func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0))
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= day_start,
                PaymentReceipt.occurred_at < day_end,
            )
            .scalar()
            or 0
        )
        revenue_this_month_minor = int(
            self.db.query(func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0))
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= month_start_dt,
                PaymentReceipt.occurred_at < month_end_dt,
            )
            .scalar()
            or 0
        )

        refunds_today_minor = int(
            self.db.query(func.coalesce(func.sum(BillingRefund.amount_minor), 0))
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.status == "PROCESSED",
                BillingRefund.processed_at >= day_start,
                BillingRefund.processed_at < day_end,
            )
            .scalar()
            or 0
        )
        refunds_this_month_minor = int(
            self.db.query(func.coalesce(func.sum(BillingRefund.amount_minor), 0))
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.status == "PROCESSED",
                BillingRefund.processed_at >= month_start_dt,
                BillingRefund.processed_at < month_end_dt,
            )
            .scalar()
            or 0
        )

        outstanding_bills_minor = int(
            self.db.query(
                func.coalesce(func.sum(BillingItem.total_minor - BillingItem.amount_paid_minor), 0)
            )
            .filter(
                BillingItem.clinic_id == clinic_id,
                BillingItem.total_minor > BillingItem.amount_paid_minor,
                BillingItem.status.in_([BillingItemStatus.PENDING]),
            )
            .scalar()
            or 0
        )

        currency = self._resolve_currency(clinic_id=clinic_id)

        return {
            "date": for_date,
            "currency": currency,
            "revenue_today_minor": revenue_today_minor,
            "revenue_this_month_minor": revenue_this_month_minor,
            "outstanding_bills_minor": outstanding_bills_minor,
            "refunds_today_minor": refunds_today_minor,
            "net_revenue_minor": revenue_this_month_minor - refunds_this_month_minor,
        }

    def list_revenue_by_department(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        start_dt, end_dt, _, _ = self._range_bounds(
            start_date=start_date,
            end_date=end_date,
        )

        leaf_sl = aliased(ServiceLine)
        root_sl = aliased(ServiceLine)
        department = aliased(Department)
        sum_expr = func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0)

        rows = (
            self.db.query(
                department.id.label("department_id"),
                func.coalesce(department.name, literal("Unassigned")).label(
                    "department_name"
                ),
                sum_expr.label("revenue_minor"),
            )
            .outerjoin(
                Visit,
                and_(
                    Visit.id == PaymentReceipt.visit_id,
                    Visit.clinic_id == PaymentReceipt.clinic_id,
                ),
            )
            .outerjoin(
                leaf_sl,
                and_(
                    leaf_sl.id == Visit.service_line_id,
                    leaf_sl.clinic_id == Visit.clinic_id,
                ),
            )
            .outerjoin(
                root_sl,
                and_(
                    root_sl.id == leaf_sl.parent_id,
                    root_sl.clinic_id == leaf_sl.clinic_id,
                ),
            )
            .outerjoin(
                department,
                and_(
                    department.id == func.coalesce(leaf_sl.department_id, root_sl.department_id),
                    department.clinic_id == PaymentReceipt.clinic_id,
                ),
            )
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= start_dt,
                PaymentReceipt.occurred_at < end_dt,
            )
            .group_by(department.id, department.name)
            .order_by(sum_expr.desc())
            .all()
        )

        total_minor = int(sum(int(row.revenue_minor or 0) for row in rows))
        if total_minor <= 0:
            return []

        return [
            {
                "department_id": row.department_id,
                "department_name": row.department_name,
                "revenue_minor": int(row.revenue_minor or 0),
                "percentage": round((int(row.revenue_minor or 0) / total_minor) * 100, 2),
            }
            for row in rows
        ]

    def list_payment_methods(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        start_dt, end_dt, _, _ = self._range_bounds(
            start_date=start_date,
            end_date=end_date,
        )

        rows = (
            self.db.query(
                PaymentReceipt.payment_method,
                func.count(PaymentReceipt.id).label("count"),
                func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0).label(
                    "total_minor"
                ),
            )
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= start_dt,
                PaymentReceipt.occurred_at < end_dt,
            )
            .group_by(PaymentReceipt.payment_method)
            .order_by(func.sum(PaymentReceipt.total_amount_minor).desc())
            .all()
        )

        gross_total = int(sum(int(row.total_minor or 0) for row in rows))
        if gross_total <= 0:
            return []

        return [
            {
                "payment_method": row.payment_method,
                "total_minor": int(row.total_minor or 0),
                "count": int(row.count or 0),
                "percentage": round((int(row.total_minor or 0) / gross_total) * 100, 2),
            }
            for row in rows
        ]

    def _build_shift_summary(
        self,
        *,
        clinic_id: UUID,
        shift: CashierShift,
        cashier_name: str | None,
        currency: str,
    ) -> dict:
        expected_total_minor = self._expected_shift_total_minor(clinic_id=clinic_id, shift=shift)
        counted_total_minor = shift.closing_cash_minor
        variance_minor = (
            expected_total_minor - counted_total_minor
            if counted_total_minor is not None
            else None
        )
        return {
            "id": shift.id,
            "cashier_id": shift.cashier_id,
            "cashier_name": cashier_name,
            "status": shift.status,
            "shift_start": shift.started_at,
            "shift_end": shift.ended_at,
            "expected_total_minor": expected_total_minor,
            "counted_total_minor": counted_total_minor,
            "variance_minor": variance_minor,
            "closing_note": shift.closing_note,
            "currency": currency,
        }

    def list_cashier_sessions(
        self,
        *,
        clinic_id: UUID,
        status_filter: str | None = None,
        for_date: date | None = None,
        cashier_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        query = (
            self.db.query(CashierShift, User.full_name.label("cashier_name"))
            .join(User, User.id == CashierShift.cashier_id)
            .filter(CashierShift.clinic_id == clinic_id)
        )

        if status_filter:
            normalized = status_filter.strip().upper()
            if normalized not in {"OPEN", "CLOSED", "RECONCILED"}:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="status must be OPEN, CLOSED, or RECONCILED",
                )
            query = query.filter(CashierShift.status == normalized)
        if cashier_id:
            query = query.filter(CashierShift.cashier_id == cashier_id)
        if for_date:
            day_start, day_end = self._day_bounds(for_date)
            query = query.filter(
                CashierShift.started_at >= day_start,
                CashierShift.started_at < day_end,
            )

        total = int(query.count())
        rows = (
            query.order_by(CashierShift.started_at.desc()).offset(offset).limit(limit).all()
        )

        currency = self._resolve_currency(clinic_id=clinic_id)
        data = [
            self._build_shift_summary(
                clinic_id=clinic_id,
                shift=shift,
                cashier_name=cashier_name,
                currency=currency,
            )
            for shift, cashier_name in rows
        ]

        return {
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_cashier_session_detail(self, *, clinic_id: UUID, session_id: UUID) -> dict:
        row = (
            self.db.query(CashierShift, User.full_name.label("cashier_name"))
            .join(User, User.id == CashierShift.cashier_id)
            .filter(
                CashierShift.clinic_id == clinic_id,
                CashierShift.id == session_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cashier session not found",
            )

        shift, cashier_name = row
        end_dt = shift.ended_at or datetime.now(timezone.utc)
        currency = self._resolve_currency(clinic_id=clinic_id)

        session_summary = self._build_shift_summary(
            clinic_id=clinic_id,
            shift=shift,
            cashier_name=cashier_name,
            currency=currency,
        )

        payment_rows = (
            self.db.query(
                PaymentReceipt,
                Patient.full_name.label("patient_name"),
                User.full_name.label("actor_name"),
            )
            .join(
                Patient,
                and_(
                    Patient.id == PaymentReceipt.patient_id,
                    Patient.clinic_id == PaymentReceipt.clinic_id,
                ),
            )
            .join(User, User.id == PaymentReceipt.collected_by)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.collected_by == shift.cashier_id,
                PaymentReceipt.occurred_at >= shift.started_at,
                PaymentReceipt.occurred_at <= end_dt,
            )
            .order_by(PaymentReceipt.occurred_at.desc())
            .all()
        )

        refund_rows = (
            self.db.query(
                BillingRefund,
                PaymentReceipt.receipt_number.label("receipt_number"),
                Patient.full_name.label("patient_name"),
                User.full_name.label("actor_name"),
            )
            .join(
                PaymentReceipt,
                and_(
                    PaymentReceipt.id == BillingRefund.receipt_id,
                    PaymentReceipt.clinic_id == BillingRefund.clinic_id,
                ),
            )
            .join(
                Patient,
                and_(
                    Patient.id == PaymentReceipt.patient_id,
                    Patient.clinic_id == PaymentReceipt.clinic_id,
                ),
            )
            .join(User, User.id == BillingRefund.processed_by)
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.processed_by == shift.cashier_id,
                BillingRefund.status == "PROCESSED",
                BillingRefund.processed_at >= shift.started_at,
                BillingRefund.processed_at <= end_dt,
            )
            .order_by(BillingRefund.processed_at.desc())
            .all()
        )

        transactions: list[dict] = []
        for receipt, patient_name, actor_name in payment_rows:
            transactions.append(
                {
                    "id": receipt.id,
                    "transaction_type": "PAYMENT",
                    "occurred_at": receipt.occurred_at,
                    "reference": receipt.receipt_number,
                    "patient_name": patient_name,
                    "amount_minor": int(receipt.total_amount_minor),
                    "currency": receipt.currency,
                    "payment_method": receipt.payment_method,
                    "actor_name": actor_name,
                    "note": receipt.notes,
                }
            )

        for refund, receipt_number, patient_name, actor_name in refund_rows:
            transactions.append(
                {
                    "id": refund.id,
                    "transaction_type": "REFUND",
                    "occurred_at": refund.processed_at,
                    "reference": receipt_number,
                    "patient_name": patient_name,
                    "amount_minor": int(refund.amount_minor),
                    "currency": refund.currency,
                    "payment_method": None,
                    "actor_name": actor_name,
                    "note": refund.reason,
                }
            )

        transactions.sort(key=lambda item: item["occurred_at"], reverse=True)

        payments_total_minor = int(
            sum(int(item["amount_minor"]) for item in transactions if item["transaction_type"] == "PAYMENT")
        )
        refunds_total_minor = int(
            sum(int(item["amount_minor"]) for item in transactions if item["transaction_type"] == "REFUND")
        )

        return {
            "session": session_summary,
            "payments_total_minor": payments_total_minor,
            "refunds_total_minor": refunds_total_minor,
            "net_total_minor": payments_total_minor - refunds_total_minor,
            "transactions": transactions,
        }

    def list_refunds(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        cashier_id: UUID | None = None,
        min_amount_minor: int | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        query = (
            self.db.query(
                BillingRefund,
                PaymentReceipt.receipt_number.label("receipt_number"),
                Patient.full_name.label("patient_name"),
                User.full_name.label("cashier_name"),
            )
            .join(
                PaymentReceipt,
                and_(
                    PaymentReceipt.id == BillingRefund.receipt_id,
                    PaymentReceipt.clinic_id == BillingRefund.clinic_id,
                ),
            )
            .join(
                Patient,
                and_(
                    Patient.id == PaymentReceipt.patient_id,
                    Patient.clinic_id == PaymentReceipt.clinic_id,
                ),
            )
            .join(User, User.id == BillingRefund.processed_by)
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.status == "PROCESSED",
            )
        )

        if start_date or end_date:
            start_dt, end_dt, _, _ = self._range_bounds(
                start_date=start_date,
                end_date=end_date,
            )
            query = query.filter(
                BillingRefund.processed_at >= start_dt,
                BillingRefund.processed_at < end_dt,
            )
        if cashier_id:
            query = query.filter(BillingRefund.processed_by == cashier_id)
        if min_amount_minor is not None:
            query = query.filter(BillingRefund.amount_minor >= min_amount_minor)

        total = int(query.count())
        rows = (
            query.order_by(BillingRefund.processed_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        data = [
            {
                "id": refund.id,
                "receipt_id": refund.receipt_id,
                "receipt_number": receipt_number,
                "patient_name": patient_name,
                "cashier_name": cashier_name,
                "amount_minor": int(refund.amount_minor),
                "currency": refund.currency,
                "reason": refund.reason,
                "status": refund.status,
                "processed_at": refund.processed_at,
            }
            for refund, receipt_number, patient_name, cashier_name in rows
        ]
        return {
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def list_refund_reasons(
        self,
        *,
        clinic_id: UUID,
        include_inactive: bool = False,
    ) -> list[dict]:
        query = self.db.query(RefundReason).filter(RefundReason.clinic_id == clinic_id)
        if not include_inactive:
            query = query.filter(RefundReason.is_active.is_(True))
        rows = query.order_by(RefundReason.reason_code.asc()).all()

        if not rows and not include_inactive:
            defaults = [
                RefundReason(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    reason_code=reason_code,
                    description=description,
                    is_active=True,
                )
                for reason_code, description in self.DEFAULT_REFUND_REASONS
            ]
            self.db.add_all(defaults)
            self.db.commit()
            rows = (
                self.db.query(RefundReason)
                .filter(
                    RefundReason.clinic_id == clinic_id,
                    RefundReason.is_active.is_(True),
                )
                .order_by(RefundReason.reason_code.asc())
                .all()
            )

        return [
            {
                "id": reason.id,
                "reason_code": reason.reason_code,
                "description": reason.description,
                "is_active": reason.is_active,
            }
            for reason in rows
        ]

    def list_outstanding_bills(
        self,
        *,
        clinic_id: UUID,
        department_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        latest_item = aliased(BillingItem)
        latest_visit_subquery = (
            self.db.query(latest_item.visit_id)
            .filter(
                latest_item.clinic_id == clinic_id,
                latest_item.patient_id == Patient.id,
                latest_item.total_minor > latest_item.amount_paid_minor,
                latest_item.status == BillingItemStatus.PENDING,
            )
        )
        latest_visit_subquery = self._apply_department_scope(
            query=latest_visit_subquery,
            billing_item_entity=latest_item,
            department_id=department_id,
        )
        latest_visit_id = (
            latest_visit_subquery.order_by(
                latest_item.updated_at.desc(),
                latest_item.created_at.desc(),
            )
            .limit(1)
            .correlate(Patient)
            .scalar_subquery()
        )

        query = (
            self.db.query(
                Patient.id.label("patient_id"),
                Patient.full_name.label("patient_name"),
                func.coalesce(
                    func.sum(BillingItem.total_minor - BillingItem.amount_paid_minor),
                    0,
                ).label("outstanding_minor"),
                func.count(func.distinct(BillingItem.visit_id)).label("visits_count"),
                latest_visit_id.label("last_visit_id"),
            )
            .join(
                Patient,
                and_(
                    Patient.id == BillingItem.patient_id,
                    Patient.clinic_id == BillingItem.clinic_id,
                ),
            )
            .filter(
                BillingItem.clinic_id == clinic_id,
                BillingItem.total_minor > BillingItem.amount_paid_minor,
                BillingItem.status == BillingItemStatus.PENDING,
            )
        )

        query = self._apply_department_scope(
            query=query,
            billing_item_entity=BillingItem,
            department_id=department_id,
        )

        grouped = query.group_by(Patient.id, Patient.full_name).subquery()
        total = int(self.db.query(func.count()).select_from(grouped).scalar() or 0)
        rows = (
            self.db.query(grouped)
            .order_by(grouped.c.outstanding_minor.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        currency = self._resolve_currency(clinic_id=clinic_id)
        data = [
            {
                "patient_id": row.patient_id,
                "patient_name": row.patient_name,
                "outstanding_minor": int(row.outstanding_minor or 0),
                "currency": currency,
                "visits_count": int(row.visits_count or 0),
                "last_visit_id": row.last_visit_id,
            }
            for row in rows
        ]
        return {
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_audit_feed(
        self,
        *,
        clinic_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        window = max(limit + offset + 25, 100)
        items: list[dict] = []

        payment_rows = (
            self.db.query(PaymentReceipt, User.full_name.label("actor_name"))
            .join(User, User.id == PaymentReceipt.collected_by)
            .filter(PaymentReceipt.clinic_id == clinic_id)
            .order_by(PaymentReceipt.occurred_at.desc())
            .limit(window)
            .all()
        )
        for receipt, actor_name in payment_rows:
            items.append(
                {
                    "id": receipt.id,
                    "event_type": "PAYMENT_POSTED",
                    "occurred_at": receipt.occurred_at,
                    "actor_name": actor_name,
                    "amount_minor": int(receipt.total_amount_minor),
                    "currency": receipt.currency,
                    "reference": receipt.receipt_number,
                    "detail": f"Payment captured via {receipt.payment_method}",
                    "severity": "info",
                }
            )

        refund_rows = (
            self.db.query(
                BillingRefund,
                PaymentReceipt.receipt_number.label("receipt_number"),
                User.full_name.label("actor_name"),
            )
            .join(
                PaymentReceipt,
                and_(
                    PaymentReceipt.id == BillingRefund.receipt_id,
                    PaymentReceipt.clinic_id == BillingRefund.clinic_id,
                ),
            )
            .join(User, User.id == BillingRefund.processed_by)
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.status == "PROCESSED",
            )
            .order_by(BillingRefund.processed_at.desc())
            .limit(window)
            .all()
        )
        for refund, receipt_number, actor_name in refund_rows:
            items.append(
                {
                    "id": refund.id,
                    "event_type": "REFUND_ISSUED",
                    "occurred_at": refund.processed_at,
                    "actor_name": actor_name,
                    "amount_minor": int(refund.amount_minor),
                    "currency": refund.currency,
                    "reference": receipt_number,
                    "detail": refund.reason,
                    "severity": "warning" if refund.amount_minor >= self.LARGE_REFUND_THRESHOLD_MINOR else "info",
                }
            )

        reprint_rows = (
            self.db.query(
                ReceiptReprintLog,
                PaymentReceipt.receipt_number.label("receipt_number"),
                User.full_name.label("actor_name"),
            )
            .join(
                PaymentReceipt,
                and_(
                    PaymentReceipt.id == ReceiptReprintLog.receipt_id,
                    PaymentReceipt.clinic_id == ReceiptReprintLog.clinic_id,
                ),
            )
            .join(User, User.id == ReceiptReprintLog.reprinted_by)
            .filter(ReceiptReprintLog.clinic_id == clinic_id)
            .order_by(ReceiptReprintLog.reprinted_at.desc())
            .limit(window)
            .all()
        )
        for reprint, receipt_number, actor_name in reprint_rows:
            items.append(
                {
                    "id": reprint.id,
                    "event_type": "RECEIPT_REPRINTED",
                    "occurred_at": reprint.reprinted_at,
                    "actor_name": actor_name,
                    "amount_minor": None,
                    "currency": None,
                    "reference": receipt_number,
                    "detail": reprint.reason or "Receipt reprint logged",
                    "severity": "warning",
                }
            )

        shift_rows = (
            self.db.query(CashierShift, User.full_name.label("actor_name"))
            .join(User, User.id == CashierShift.cashier_id)
            .filter(
                CashierShift.clinic_id == clinic_id,
                CashierShift.status.in_(["CLOSED", "RECONCILED"]),
            )
            .order_by(CashierShift.ended_at.desc())
            .limit(window)
            .all()
        )
        for shift, actor_name in shift_rows:
            expected_total = self._expected_shift_total_minor(clinic_id=clinic_id, shift=shift)
            counted_total = shift.closing_cash_minor
            variance = (
                expected_total - counted_total if counted_total is not None else None
            )
            items.append(
                {
                    "id": shift.id,
                    "event_type": "SHIFT_CLOSED",
                    "occurred_at": shift.ended_at or shift.started_at,
                    "actor_name": actor_name,
                    "amount_minor": variance,
                    "currency": self._resolve_currency(clinic_id=clinic_id),
                    "reference": str(shift.id),
                    "detail": (
                        f"Shift closed with variance {variance}"
                        if variance is not None
                        else "Shift closed"
                    ),
                    "severity": (
                        "warning"
                        if variance is not None
                        and abs(variance) > self.VARIANCE_THRESHOLD_MINOR
                        else "info"
                    ),
                }
            )

        items.sort(key=lambda item: item["occurred_at"], reverse=True)
        total = len(items)
        return {
            "data": items[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_fraud_signals(self, *, clinic_id: UUID, for_date: date) -> dict:
        day_start, day_end = self._day_bounds(for_date)

        large_refunds_count = int(
            self.db.query(func.count(BillingRefund.id))
            .filter(
                BillingRefund.clinic_id == clinic_id,
                BillingRefund.status == "PROCESSED",
                BillingRefund.processed_at >= day_start,
                BillingRefund.processed_at < day_end,
                BillingRefund.amount_minor >= self.LARGE_REFUND_THRESHOLD_MINOR,
            )
            .scalar()
            or 0
        )
        reprints_today_count = int(
            self.db.query(func.count(ReceiptReprintLog.id))
            .filter(
                ReceiptReprintLog.clinic_id == clinic_id,
                ReceiptReprintLog.reprinted_at >= day_start,
                ReceiptReprintLog.reprinted_at < day_end,
            )
            .scalar()
            or 0
        )
        cash_total_today_minor = int(
            self.db.query(func.coalesce(func.sum(PaymentReceipt.total_amount_minor), 0))
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= day_start,
                PaymentReceipt.occurred_at < day_end,
                PaymentReceipt.payment_method == BillingReasonCode.CASH,
            )
            .scalar()
            or 0
        )

        shift_rows = (
            self.db.query(CashierShift)
            .filter(
                CashierShift.clinic_id == clinic_id,
                CashierShift.status.in_(["CLOSED", "RECONCILED"]),
                CashierShift.started_at >= day_start,
                CashierShift.started_at < day_end,
                CashierShift.closing_cash_minor.isnot(None),
            )
            .all()
        )
        open_variances_count = 0
        for shift in shift_rows:
            expected = self._expected_shift_total_minor(clinic_id=clinic_id, shift=shift)
            variance = expected - int(shift.closing_cash_minor or 0)
            if abs(variance) > self.VARIANCE_THRESHOLD_MINOR:
                open_variances_count += 1

        currency = self._resolve_currency(clinic_id=clinic_id)
        return {
            "date": for_date,
            "currency": currency,
            "large_refunds_count": large_refunds_count,
            "reprints_today_count": reprints_today_count,
            "open_variances_count": open_variances_count,
            "cash_total_today_minor": cash_total_today_minor,
            "high_cash_today": cash_total_today_minor >= self.HIGH_CASH_THRESHOLD_MINOR,
            "thresholds": {
                "large_refund_minor": self.LARGE_REFUND_THRESHOLD_MINOR,
                "variance_minor": self.VARIANCE_THRESHOLD_MINOR,
                "high_cash_minor": self.HIGH_CASH_THRESHOLD_MINOR,
            },
        }

    def reconcile_cashier_session(
        self,
        *,
        clinic_id: UUID,
        session_id: UUID,
        actor,
        idempotency_key: str,
        counted_total_minor: int | None = None,
        closing_note: str | None = None,
    ) -> dict:
        endpoint = "ACCOUNTANT_SHIFT_RECONCILE"
        existing = (
            self.db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.key == idempotency_key,
                IdempotencyKey.endpoint == endpoint,
                IdempotencyKey.user_id == actor.id,
            )
            .first()
        )
        if existing:
            return existing.response_body

        shift = (
            self.db.query(CashierShift)
            .filter(
                CashierShift.clinic_id == clinic_id,
                CashierShift.id == session_id,
            )
            .first()
        )
        if shift is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cashier session not found",
            )
        if shift.status == "OPEN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Close the session before reconciliation",
            )

        now = datetime.now(timezone.utc)
        if counted_total_minor is not None:
            shift.closing_cash_minor = counted_total_minor
        if closing_note:
            shift.closing_note = closing_note.strip()

        expected_total_minor = self._expected_shift_total_minor(clinic_id=clinic_id, shift=shift)
        variance_minor = (
            expected_total_minor - int(shift.closing_cash_minor)
            if shift.closing_cash_minor is not None
            else None
        )

        shift.status = "RECONCILED"
        if hasattr(shift, "reconciled_by"):
            shift.reconciled_by = actor.id
        if hasattr(shift, "reconciled_at"):
            shift.reconciled_at = now

        response_payload = {
            "session_id": str(shift.id),
            "status": shift.status,
            "counted_total_minor": shift.closing_cash_minor,
            "variance_minor": variance_minor,
            "reconciled_at": now.isoformat(),
        }

        self.db.add(shift)
        self.db.add(
            IdempotencyKey(
                id=uuid.uuid4(),
                key=idempotency_key,
                user_id=actor.id,
                endpoint=endpoint,
                request_hash=self._hash_request(
                    {
                        "session_id": str(session_id),
                        "counted_total_minor": counted_total_minor,
                        "closing_note": closing_note,
                    }
                ),
                response_body=response_payload,
            )
        )
        self.db.commit()
        return response_payload

    def export_csv_report(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        payment_method: BillingReasonCode | None = None,
    ) -> str:
        start_dt, end_dt, resolved_start, resolved_end = self._range_bounds(
            start_date=start_date,
            end_date=end_date,
        )

        query = (
            self.db.query(
                PaymentReceipt,
                Patient.full_name.label("patient_name"),
                User.full_name.label("cashier_name"),
            )
            .join(
                Patient,
                and_(
                    Patient.id == PaymentReceipt.patient_id,
                    Patient.clinic_id == PaymentReceipt.clinic_id,
                ),
            )
            .join(User, User.id == PaymentReceipt.collected_by)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= start_dt,
                PaymentReceipt.occurred_at < end_dt,
            )
        )
        if payment_method is not None:
            query = query.filter(PaymentReceipt.payment_method == payment_method)

        rows = query.order_by(PaymentReceipt.occurred_at.desc()).all()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Period Start",
                "Period End",
                "Receipt Number",
                "Occurred At (UTC)",
                "Patient",
                "Visit ID",
                "Method",
                "Amount (minor)",
                "Currency",
                "Collected By",
            ]
        )
        for receipt, patient_name, cashier_name in rows:
            writer.writerow(
                [
                    resolved_start.isoformat(),
                    resolved_end.isoformat(),
                    receipt.receipt_number,
                    receipt.occurred_at.isoformat(),
                    patient_name or "",
                    str(receipt.visit_id),
                    receipt.payment_method.value
                    if isinstance(receipt.payment_method, BillingReasonCode)
                    else receipt.payment_method,
                    int(receipt.total_amount_minor),
                    receipt.currency,
                    cashier_name or "",
                ]
            )
        return output.getvalue()
