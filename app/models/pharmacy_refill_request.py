import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PharmacyRefillRequestStatus, PharmacyRequestType


class PharmacyRefillRequest(Base):
    __tablename__ = "pharmacy_refill_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    requesting_unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    request_type: Mapped[PharmacyRequestType] = mapped_column(
        String(40),
        nullable=False,
        default=PharmacyRequestType.PHARMACY_REFILL.value,
        server_default=PharmacyRequestType.PHARMACY_REFILL.value,
    )
    status: Mapped[PharmacyRefillRequestStatus] = mapped_column(
        Enum(PharmacyRefillRequestStatus, name="pharmacy_refill_request_status"),
        nullable=False,
        default=PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL,
        server_default=PharmacyRefillRequestStatus.AWAITING_CMD_APPROVAL.value,
    )
    urgency: Mapped[str | None] = mapped_column(String(40), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    hod_visible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_refill_requests_id_clinic"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_refill_requests_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requesting_unit_id"],
            ["service_lines.id"],
            name="fk_pharmacy_refill_requests_requesting_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_pharmacy_refill_requests_requested_by",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_pharmacy_refill_requests_reviewed_by",
            ondelete="SET NULL",
        ),
    )
