from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditTimelineItem(BaseModel):
    id: UUID
    source: str  # "EVENT" | "ACCESS"
    event_type: str
    actor_id: Optional[UUID]
    actor_role: str
    clinic_id: UUID
    patient_id: Optional[UUID]
    resource: Optional[str] = None
    break_glass: Optional[bool] = None
    event_payload: Optional[dict[str, Any]] = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicHealthSnapshot(BaseModel):
    active_visits: int
    active_staff: int
    break_glass_24h: int


class StaffActivityBucket(BaseModel):
    hour: datetime
    activity_type: str
    actor_role: str
    count: int


class SystemPerformanceMetrics(BaseModel):
    avg_triage_wait_minutes: Optional[float]
    triage_samples: int
    avg_consult_wait_minutes: Optional[float]
    consult_samples: int
    avg_lab_turnaround_minutes: Optional[float]
    lab_samples: int


class ComplianceSummary(BaseModel):
    break_glass_24h: int
    open_audit_cases: int
    failed_logins_24h: int


class PaymentOversight(BaseModel):
    currency: str
    charges_today_minor: int
    payments_today_minor: int
    refunds_today_minor: int
    writeoffs_today_minor: int
    net_today_minor: int
    registration_fee_count_today: int
    registration_fee_total_minor: int


class PatientMetrics(BaseModel):
    total_patients: int
    registered_today: int


class PaymentDashboardOverview(BaseModel):
    currency: str
    today_revenue_minor: int
    monthly_target_minor: int
    monthly_progress_pct: float
    outstanding_minor: int
    collection_rate_pct: float
    transactions_today: int
    avg_transaction_minor: int
    peak_hour: Optional[str]


class TransactionVelocityItem(BaseModel):
    occurred_at: datetime
    amount_minor: int


class PaymentTransactionItem(BaseModel):
    occurred_at: datetime
    patient_name: Optional[str]
    service: str
    amount_minor: int
    method: Optional[str]
    status: str
    note: Optional[str] = None


class PaymentCategoryItem(BaseModel):
    category: str
    amount_minor: int
    percent: float


class PaymentMethodItem(BaseModel):
    method: str
    amount_minor: int
    percent: float


class TopServiceItem(BaseModel):
    service: str
    amount_minor: int
    count: int


class PaymentAlertItem(BaseModel):
    severity: str
    message: str


class OutstandingBalanceItem(BaseModel):
    patient_id: UUID
    patient_name: Optional[str]
    balance_minor: int
    days_since_last_payment: Optional[int]


class ChargeCatalogItem(BaseModel):
    id: UUID
    code: str
    name: str
    category: str
    default_amount_minor: int
    currency: str
    active: bool
    usage_today_count: int
    usage_today_minor: int


class PaymentDashboardResponse(BaseModel):
    overview: PaymentDashboardOverview
    velocity: list[TransactionVelocityItem]
    transactions: list[PaymentTransactionItem]
    category_breakdown: list[PaymentCategoryItem]
    top_services: list[TopServiceItem]
    method_breakdown: list[PaymentMethodItem]
    alerts: list[PaymentAlertItem]
    insights: list[str]
    outstanding_balances: list[OutstandingBalanceItem]


class ChargeCatalogCreateRequest(BaseModel):
    code: str
    name: str
    category: str
    default_amount_minor: int
    currency: str
    active: bool = True


class ChargeCatalogUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    default_amount_minor: Optional[int] = None
    currency: Optional[str] = None
    active: Optional[bool] = None
