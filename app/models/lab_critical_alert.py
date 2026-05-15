import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import (
    LabCriticalAlertSeverity,
    LabCriticalAlertStatus,
    LabCriticalAlertType,
)


class LabCriticalAlert(Base):
    __tablename__ = "lab_critical_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    result_value_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    request_item_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    alert_type: Mapped[LabCriticalAlertType] = mapped_column(
        Enum(LabCriticalAlertType, name="lab_critical_alert_type"),
        nullable=False,
    )
    severity: Mapped[LabCriticalAlertSeverity] = mapped_column(
        Enum(LabCriticalAlertSeverity, name="lab_critical_alert_severity"),
        nullable=False,
        default=LabCriticalAlertSeverity.CRITICAL,
        server_default=LabCriticalAlertSeverity.CRITICAL.value,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[str] = mapped_column(String(64), nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[LabCriticalAlertStatus] = mapped_column(
        Enum(LabCriticalAlertStatus, name="lab_critical_alert_status"),
        nullable=False,
        default=LabCriticalAlertStatus.CREATED,
        server_default=LabCriticalAlertStatus.CREATED.value,
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["result_id"],
            ["lab_results.id"],
            name="fk_lab_critical_alerts_result",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["result_value_id"],
            ["lab_result_values.id"],
            name="fk_lab_critical_alerts_result_value",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["request_item_id"],
            ["lab_requests.id"],
            name="fk_lab_critical_alerts_request_item",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["visit_id"],
            ["visits.id"],
            name="fk_lab_critical_alerts_visit",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_lab_critical_alerts_patient",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["unit_id"],
            ["service_lines.id"],
            name="fk_lab_critical_alerts_unit",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_lab_critical_alerts_target_user",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
            name="fk_lab_critical_alerts_acknowledged_by",
            ondelete="SET NULL",
        ),
    )
