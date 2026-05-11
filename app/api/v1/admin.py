from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.rbac import require_clinic_admin
from app.models.access_log import AccessLog
from app.models.audit_review_case import AuditReviewCase
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.consultation import Consultation
from app.models.event_log import EventLog
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.schemas.admin import (
    AuditTimelineItem,
    ClinicHealthSnapshot,
    StaffActivityBucket,
    SystemPerformanceMetrics,
    ComplianceSummary,
    PaymentDashboardResponse,
    PaymentDashboardOverview,
    TransactionVelocityItem,
    PaymentTransactionItem,
    PaymentCategoryItem,
    PaymentMethodItem,
    TopServiceItem,
    PaymentAlertItem,
    OutstandingBalanceItem,
    ChargeCatalogItem,
    PatientMetrics,
    ChargeCatalogCreateRequest,
    ChargeCatalogUpdateRequest,
)
from app.schemas.pharmacy_catalog import PharmacyCatalogRegistryRowResponse
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.shared.enums import (
    UserRole,
    VisitStatus,
    AuditCaseStatus,
    BillingEntryType,
    BillingReasonCode,
)


router = APIRouter(prefix="/admin", tags=["Admin"])


def _parse_datetime(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid datetime format",
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.get(
    "/audit-timeline",
    response_model=list[AuditTimelineItem],
    status_code=status.HTTP_200_OK,
)
def get_audit_timeline(
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    event_type: str | None = Query(default=None),
    actor_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    start = _parse_datetime(from_dt)
    end = _parse_datetime(to_dt)

    event_query = db.query(EventLog).filter(EventLog.clinic_id == current_user.clinic_id)
    access_query = db.query(AccessLog).filter(AccessLog.clinic_id == current_user.clinic_id)

    if start is not None:
        event_query = event_query.filter(EventLog.created_at >= start)
        access_query = access_query.filter(AccessLog.created_at >= start)
    if end is not None:
        event_query = event_query.filter(EventLog.created_at <= end)
        access_query = access_query.filter(AccessLog.created_at <= end)
    if actor_id is not None:
        event_query = event_query.filter(EventLog.actor_id == actor_id)
        access_query = access_query.filter(AccessLog.actor_id == actor_id)
    if event_type:
        event_query = event_query.filter(EventLog.event_type == event_type)
        access_query = access_query.filter(AccessLog.action == event_type)

    events = event_query.order_by(EventLog.created_at.desc()).limit(limit).all()
    accesses = access_query.order_by(AccessLog.created_at.desc()).limit(limit).all()

    items: list[AuditTimelineItem] = []
    for event in events:
        items.append(
            AuditTimelineItem(
                id=event.id,
                source="EVENT",
                event_type=event.event_type,
                actor_id=event.actor_id,
                actor_role=event.actor_role,
                clinic_id=event.clinic_id,
                patient_id=event.patient_id,
                resource=None,
                break_glass=None,
                occurred_at=event.created_at,
            )
        )
    for access in accesses:
        items.append(
            AuditTimelineItem(
                id=access.id,
                source="ACCESS",
                event_type=access.action,
                actor_id=access.actor_id,
                actor_role=access.actor_role,
                clinic_id=access.clinic_id,
                patient_id=access.patient_id,
                resource=access.resource,
                break_glass=access.break_glass,
                occurred_at=access.created_at,
            )
        )

    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items[:limit]


@router.get(
    "/clinic-health",
    response_model=ClinicHealthSnapshot,
    status_code=status.HTTP_200_OK,
)
def get_clinic_health(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    active_statuses = {
        VisitStatus.REGISTERED,
        VisitStatus.TRIAGED,
        VisitStatus.IN_CONSULTATION,
        VisitStatus.LAB_REQUESTED,
        VisitStatus.LAB_COMPLETED,
        VisitStatus.PHARMACY_PENDING,
    }
    active_visits = (
        db.query(Visit)
        .filter(
            Visit.clinic_id == current_user.clinic_id,
            Visit.status.in_(active_statuses),
        )
        .count()
    )
    active_staff = (
        db.query(User)
        .filter(
            User.clinic_id == current_user.clinic_id,
            User.is_active.is_(True),
            User.role != UserRole.SYSTEM,
        )
        .count()
    )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    break_glass = (
        db.query(AccessLog)
        .filter(
            AccessLog.clinic_id == current_user.clinic_id,
            AccessLog.break_glass.is_(True),
            AccessLog.created_at >= cutoff,
        )
        .count()
    )

    return ClinicHealthSnapshot(
        active_visits=active_visits,
        active_staff=active_staff,
        break_glass_24h=break_glass,
    )


@router.get(
    "/staff-activity",
    response_model=list[StaffActivityBucket],
    status_code=status.HTTP_200_OK,
)
def get_staff_activity(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = (
        db.query(EventLog)
        .filter(
            EventLog.clinic_id == current_user.clinic_id,
            EventLog.event_type.in_(["VISIT_REGISTERED", "CONSULTATION_STARTED"]),
            EventLog.created_at >= cutoff,
        )
        .all()
    )

    buckets: dict[tuple[datetime, str, str], int] = {}
    for event in events:
        hour = event.created_at.replace(minute=0, second=0, microsecond=0)
        activity_type = (
            "visit_registration"
            if event.event_type == "VISIT_REGISTERED"
            else "consultation_started"
        )
        key = (hour, activity_type, event.actor_role)
        buckets[key] = buckets.get(key, 0) + 1

    response: list[StaffActivityBucket] = []
    for (hour, activity_type, actor_role), count in buckets.items():
        response.append(
            StaffActivityBucket(
                hour=hour,
                activity_type=activity_type,
                actor_role=actor_role,
                count=count,
            )
        )

    response.sort(key=lambda item: (item.hour, item.activity_type, item.actor_role))
    return response


@router.get(
    "/system-metrics",
    response_model=SystemPerformanceMetrics,
    status_code=status.HTTP_200_OK,
)
def get_system_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    triage_subq = (
        db.query(
            VisitStatusHistory.visit_id.label("visit_id"),
            func.min(VisitStatusHistory.created_at).label("triaged_at"),
        )
        .filter(VisitStatusHistory.to_status == VisitStatus.TRIAGED)
        .group_by(VisitStatusHistory.visit_id)
        .subquery()
    )

    triage_rows = (
        db.query(
            func.avg(
                func.extract(
                    "epoch",
                    triage_subq.c.triaged_at - Visit.started_at,
                )
            ).label("avg_seconds"),
            func.count().label("samples"),
        )
        .join(triage_subq, triage_subq.c.visit_id == Visit.id)
        .filter(
            Visit.clinic_id == current_user.clinic_id,
            Visit.started_at >= cutoff,
        )
        .first()
    )

    consult_rows = (
        db.query(
            func.avg(
                func.extract(
                    "epoch",
                    Consultation.started_at - triage_subq.c.triaged_at,
                )
            ).label("avg_seconds"),
            func.count().label("samples"),
        )
        .join(Visit, Consultation.visit_id == Visit.id)
        .join(triage_subq, triage_subq.c.visit_id == Visit.id)
        .filter(
            Consultation.clinic_id == current_user.clinic_id,
            Consultation.started_at >= cutoff,
        )
        .first()
    )

    lab_rows = (
        db.query(
            func.avg(
                func.extract(
                    "epoch",
                    LabResult.created_at - LabRequest.created_at,
                )
            ).label("avg_seconds"),
            func.count().label("samples"),
        )
        .join(LabRequest, LabResult.lab_request_id == LabRequest.id)
        .filter(
            LabResult.clinic_id == current_user.clinic_id,
            LabResult.created_at >= cutoff,
        )
        .first()
    )

    def _to_minutes(avg_seconds: float | None) -> float | None:
        if avg_seconds is None:
            return None
        return round(avg_seconds / 60.0, 2)

    triage_avg = _to_minutes(triage_rows.avg_seconds if triage_rows else None)
    triage_samples = int(triage_rows.samples) if triage_rows else 0
    consult_avg = _to_minutes(consult_rows.avg_seconds if consult_rows else None)
    consult_samples = int(consult_rows.samples) if consult_rows else 0
    lab_avg = _to_minutes(lab_rows.avg_seconds if lab_rows else None)
    lab_samples = int(lab_rows.samples) if lab_rows else 0

    return SystemPerformanceMetrics(
        avg_triage_wait_minutes=triage_avg,
        triage_samples=triage_samples,
        avg_consult_wait_minutes=consult_avg,
        consult_samples=consult_samples,
        avg_lab_turnaround_minutes=lab_avg,
        lab_samples=lab_samples,
    )


@router.get(
    "/compliance-summary",
    response_model=ComplianceSummary,
    status_code=status.HTTP_200_OK,
)
def get_compliance_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    break_glass = (
        db.query(AccessLog)
        .filter(
            AccessLog.clinic_id == current_user.clinic_id,
            AccessLog.break_glass.is_(True),
            AccessLog.created_at >= cutoff,
        )
        .count()
    )

    open_cases = (
        db.query(AuditReviewCase)
        .filter(
            AuditReviewCase.clinic_id == current_user.clinic_id,
            AuditReviewCase.status.in_(
                [AuditCaseStatus.OPEN, AuditCaseStatus.IN_REVIEW]
            ),
        )
        .count()
    )

    failed_logins = (
        db.query(EventLog)
        .filter(
            EventLog.clinic_id == current_user.clinic_id,
            EventLog.event_type == "LOGIN_FAILED",
            EventLog.created_at >= cutoff,
        )
        .count()
    )

    return ComplianceSummary(
        break_glass_24h=break_glass,
        open_audit_cases=open_cases,
        failed_logins_24h=failed_logins,
    )


@router.get(
    "/patient-metrics",
    response_model=PatientMetrics,
    status_code=status.HTTP_200_OK,
)
def get_patient_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_patients = (
        db.query(Patient)
        .filter(Patient.clinic_id == current_user.clinic_id)
        .count()
    )
    registered_today = (
        db.query(Patient)
        .filter(
            Patient.clinic_id == current_user.clinic_id,
            Patient.created_at >= start_of_day,
        )
        .count()
    )

    return PatientMetrics(
        total_patients=total_patients,
        registered_today=registered_today,
    )


def _category_for_charge(entry: BillingLedgerEntry) -> str:
    if entry.reason_code == BillingReasonCode.REGISTRATION_FEE:
        return "Registration"
    if entry.reason_code == BillingReasonCode.LAB_TEST:
        return "Diagnostics"
    if entry.reason_code == BillingReasonCode.MEDICATION:
        return "Pharmacy"
    if entry.reason_code == BillingReasonCode.PROCEDURE:
        return "Procedures"
    if entry.admission_id is not None:
        return "Admissions"
    if entry.reason_code == BillingReasonCode.SERVICE:
        return "Consultation"
    return "Other"


def _status_for_entry(entry: BillingLedgerEntry) -> str:
    if entry.entry_type == BillingEntryType.PAYMENT:
        return "Paid"
    if entry.entry_type == BillingEntryType.CHARGE:
        return "Charged"
    if entry.entry_type == BillingEntryType.REFUND:
        return "Refunded"
    if entry.entry_type == BillingEntryType.WRITE_OFF:
        return "Write-off"
    if entry.entry_type == BillingEntryType.REVERSAL:
        return "Reversed"
    return "Adjusted"


@router.get(
    "/payment-dashboard",
    response_model=PaymentDashboardResponse,
    status_code=status.HTTP_200_OK,
)
def get_payment_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    clinic = (
        db.query(Clinic)
        .filter(Clinic.id == current_user.clinic_id)
        .first()
    )
    currency = clinic.billing_currency if clinic else "NGN"
    monthly_target = clinic.monthly_revenue_target_minor if clinic else 0

    base_today = (
        db.query(BillingLedgerEntry)
        .filter(
            BillingLedgerEntry.clinic_id == current_user.clinic_id,
            BillingLedgerEntry.occurred_at >= start_of_day,
        )
    )

    def sum_for(entry_type: BillingEntryType) -> int:
        value = (
            base_today.filter(BillingLedgerEntry.entry_type == entry_type)
            .with_entities(func.coalesce(func.sum(BillingLedgerEntry.amount_minor), 0))
            .scalar()
        )
        return int(value or 0)

    charges_today = sum_for(BillingEntryType.CHARGE)
    payments_today = abs(sum_for(BillingEntryType.PAYMENT))
    refunds_today = sum_for(BillingEntryType.REFUND)
    writeoffs_today = abs(sum_for(BillingEntryType.WRITE_OFF))
    net_today = (
        base_today.with_entities(
            func.coalesce(func.sum(BillingLedgerEntry.amount_minor), 0)
        ).scalar()
        or 0
    )

    transactions_today = base_today.count()
    avg_transaction = 0
    if transactions_today > 0:
        avg_transaction = int(
            abs(net_today) / transactions_today
        )

    peak_hour_row = (
        base_today.with_entities(
            func.date_trunc("hour", BillingLedgerEntry.occurred_at).label("hour"),
            func.count().label("count"),
        )
        .group_by("hour")
        .order_by(func.count().desc())
        .first()
    )
    peak_hour = (
        peak_hour_row.hour.strftime("%H:00") if peak_hour_row else None
    )

    outstanding_rows = (
        db.query(
            BillingLedgerEntry.patient_id,
            func.sum(BillingLedgerEntry.amount_minor).label("balance"),
        )
        .filter(BillingLedgerEntry.clinic_id == current_user.clinic_id)
        .group_by(BillingLedgerEntry.patient_id)
        .having(func.sum(BillingLedgerEntry.amount_minor) > 0)
        .order_by(func.sum(BillingLedgerEntry.amount_minor).desc())
        .all()
    )
    outstanding_total = sum(int(row.balance) for row in outstanding_rows)

    collection_rate = 0.0
    if charges_today > 0:
        collection_rate = round((payments_today / charges_today) * 100, 1)

    month_payments = (
        db.query(BillingLedgerEntry)
        .filter(
            BillingLedgerEntry.clinic_id == current_user.clinic_id,
            BillingLedgerEntry.entry_type == BillingEntryType.PAYMENT,
            BillingLedgerEntry.occurred_at >= start_of_month,
        )
        .with_entities(func.coalesce(func.sum(BillingLedgerEntry.amount_minor), 0))
        .scalar()
        or 0
    )
    month_payments = abs(int(month_payments))
    progress_pct = (
        round((month_payments / monthly_target) * 100, 1)
        if monthly_target > 0
        else 0.0
    )

    velocity_entries = (
        base_today.order_by(BillingLedgerEntry.occurred_at.desc()).limit(4).all()
    )
    velocity = [
        TransactionVelocityItem(
            occurred_at=row.occurred_at,
            amount_minor=abs(row.amount_minor),
        )
        for row in velocity_entries
    ]

    patients = {
        patient.id: patient.full_name
        for patient in db.query(Patient)
        .filter(Patient.clinic_id == current_user.clinic_id)
        .all()
    }

    transactions = []
    feed_rows = (
        base_today.order_by(BillingLedgerEntry.occurred_at.desc()).limit(50).all()
    )
    for entry in feed_rows:
        method = None
        if entry.entry_type == BillingEntryType.PAYMENT:
            method = entry.reason_code.value
        service = entry.charge_code or entry.description
        transactions.append(
            PaymentTransactionItem(
                occurred_at=entry.occurred_at,
                patient_name=patients.get(entry.patient_id),
                service=service,
                amount_minor=abs(entry.amount_minor),
                method=method,
                status=_status_for_entry(entry),
                note=None,
            )
        )

    category_totals: dict[str, int] = {}
    charge_rows = (
        base_today.filter(BillingLedgerEntry.entry_type == BillingEntryType.CHARGE)
        .all()
    )
    for entry in charge_rows:
        category = _category_for_charge(entry)
        category_totals[category] = category_totals.get(category, 0) + int(
            entry.amount_minor
        )

    total_charges = sum(category_totals.values()) or 0
    category_breakdown = [
        PaymentCategoryItem(
            category=category,
            amount_minor=amount,
            percent=round((amount / total_charges) * 100, 1) if total_charges else 0.0,
        )
        for category, amount in sorted(category_totals.items(), key=lambda x: -x[1])
    ]

    top_services_map: dict[str, dict[str, int]] = {}
    for entry in charge_rows:
        service = entry.charge_code or entry.description
        data = top_services_map.get(service, {"amount": 0, "count": 0})
        data["amount"] += int(entry.amount_minor)
        data["count"] += 1
        top_services_map[service] = data
    top_services = sorted(
        top_services_map.items(), key=lambda x: -x[1]["amount"]
    )[:3]
    top_services_items = [
        TopServiceItem(
            service=service,
            amount_minor=data["amount"],
            count=data["count"],
        )
        for service, data in top_services
    ]

    method_totals: dict[str, int] = {}
    payments = base_today.filter(
        BillingLedgerEntry.entry_type == BillingEntryType.PAYMENT
    ).all()
    for entry in payments:
        method = entry.reason_code.value
        method_totals[method] = method_totals.get(method, 0) + abs(
            int(entry.amount_minor)
        )
    total_methods = sum(method_totals.values()) or 0
    method_breakdown = [
        PaymentMethodItem(
            method=method,
            amount_minor=amount,
            percent=round((amount / total_methods) * 100, 1) if total_methods else 0.0,
        )
        for method, amount in sorted(method_totals.items(), key=lambda x: -x[1])
    ]

    alerts: list[PaymentAlertItem] = []
    if outstanding_rows:
        high_balance = [
            row for row in outstanding_rows if row.balance >= 100000
        ]
        if high_balance:
            alerts.append(
                PaymentAlertItem(
                    severity="HIGH",
                    message=f"{len(high_balance)} patients with balances above ₦100,000",
                )
            )
    if refunds_today > 0:
        alerts.append(
            PaymentAlertItem(
                severity="MEDIUM",
                message="Refunds issued today require reconciliation",
            )
        )

    insights: list[str] = []
    if method_breakdown:
        cash_share = next(
            (item.percent for item in method_breakdown if item.method == "CASH"),
            0,
        )
        if cash_share > 50:
            insights.append("Cash dominates today’s collections. Consider banking early.")
    if category_breakdown:
        insights.append(
            f"Top revenue category today: {category_breakdown[0].category}."
        )

    last_payment_subq = (
        db.query(
            BillingLedgerEntry.patient_id.label("patient_id"),
            func.max(BillingLedgerEntry.occurred_at).label("last_payment"),
        )
        .filter(
            BillingLedgerEntry.clinic_id == current_user.clinic_id,
            BillingLedgerEntry.entry_type == BillingEntryType.PAYMENT,
        )
        .group_by(BillingLedgerEntry.patient_id)
        .subquery()
    )

    outstanding_items = []
    for row in outstanding_rows[:5]:
        last_payment = (
            db.query(last_payment_subq.c.last_payment)
            .filter(last_payment_subq.c.patient_id == row.patient_id)
            .scalar()
        )
        days_since = None
        if last_payment:
            days_since = (now - last_payment).days
        outstanding_items.append(
            OutstandingBalanceItem(
                patient_id=row.patient_id,
                patient_name=patients.get(row.patient_id),
                balance_minor=int(row.balance),
                days_since_last_payment=days_since,
            )
        )

    overview = PaymentDashboardOverview(
        currency=currency,
        today_revenue_minor=payments_today,
        monthly_target_minor=monthly_target,
        monthly_progress_pct=progress_pct,
        outstanding_minor=outstanding_total,
        collection_rate_pct=collection_rate,
        transactions_today=transactions_today,
        avg_transaction_minor=avg_transaction,
        peak_hour=peak_hour,
    )

    return PaymentDashboardResponse(
        overview=overview,
        velocity=velocity,
        transactions=transactions,
        category_breakdown=category_breakdown,
        top_services=top_services_items,
        method_breakdown=method_breakdown,
        alerts=alerts,
        insights=insights,
        outstanding_balances=outstanding_items,
    )


@router.get(
    "/charge-catalog",
    response_model=list[ChargeCatalogItem],
    status_code=status.HTTP_200_OK,
)
def list_charge_catalog(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    usage_rows = (
        db.query(
            BillingLedgerEntry.charge_code,
            func.count().label("count"),
            func.coalesce(func.sum(BillingLedgerEntry.amount_minor), 0).label("total"),
        )
        .filter(
            BillingLedgerEntry.clinic_id == current_user.clinic_id,
            BillingLedgerEntry.entry_type == BillingEntryType.CHARGE,
            BillingLedgerEntry.charge_code.isnot(None),
            BillingLedgerEntry.occurred_at >= start_of_day,
        )
        .group_by(BillingLedgerEntry.charge_code)
        .all()
    )
    usage_map = {row.charge_code: row for row in usage_rows}

    rows = (
        db.query(ChargeCatalog)
        .filter(ChargeCatalog.clinic_id == current_user.clinic_id)
        .order_by(ChargeCatalog.code.asc())
        .all()
    )

    response: list[ChargeCatalogItem] = []
    for row in rows:
        usage = usage_map.get(row.code)
        response.append(
            ChargeCatalogItem(
                id=row.id,
                code=row.code,
                name=row.name,
                category=row.category,
                default_amount_minor=row.default_amount_minor,
                currency=row.currency,
                active=row.active,
                usage_today_count=int(usage.count) if usage else 0,
                usage_today_minor=int(usage.total) if usage else 0,
            )
        )

    return response


@router.post(
    "/charge-catalog",
    response_model=ChargeCatalogItem,
    status_code=status.HTTP_201_CREATED,
)
def create_charge_catalog(
    payload: ChargeCatalogCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    exists = (
        db.query(ChargeCatalog)
        .filter(
            ChargeCatalog.clinic_id == current_user.clinic_id,
            ChargeCatalog.code == payload.code,
        )
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Charge code already exists",
        )

    item = ChargeCatalog(
        clinic_id=current_user.clinic_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        category=payload.category.strip(),
        default_amount_minor=payload.default_amount_minor,
        currency=payload.currency,
        active=payload.active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return ChargeCatalogItem(
        id=item.id,
        code=item.code,
        name=item.name,
        category=item.category,
        default_amount_minor=item.default_amount_minor,
        currency=item.currency,
        active=item.active,
        usage_today_count=0,
        usage_today_minor=0,
    )


@router.patch(
    "/charge-catalog/{catalog_id}",
    response_model=ChargeCatalogItem,
    status_code=status.HTTP_200_OK,
)
def update_charge_catalog(
    catalog_id: UUID,
    payload: ChargeCatalogUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    item = (
        db.query(ChargeCatalog)
        .filter(
            ChargeCatalog.id == catalog_id,
            ChargeCatalog.clinic_id == current_user.clinic_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Charge catalog item not found")

    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.category is not None:
        item.category = payload.category.strip()
    if payload.default_amount_minor is not None:
        item.default_amount_minor = payload.default_amount_minor
    if payload.currency is not None:
        item.currency = payload.currency
    if payload.active is not None:
        item.active = payload.active

    db.commit()
    db.refresh(item)

    return ChargeCatalogItem(
        id=item.id,
        code=item.code,
        name=item.name,
        category=item.category,
        default_amount_minor=item.default_amount_minor,
        currency=item.currency,
        active=item.active,
        usage_today_count=0,
        usage_today_minor=0,
    )


@router.get(
    "/pharmacy-catalog",
    response_model=list[PharmacyCatalogRegistryRowResponse],
    status_code=status.HTTP_200_OK,
)
def list_pharmacy_catalog_registry(
    db: Session = Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    return PharmacyCatalogGovernanceService(db).list_catalog_items(
        clinic_id=current_user.clinic_id,
    )
