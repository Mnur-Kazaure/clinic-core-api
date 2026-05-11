import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PharmacyReturnReasonCode, PharmacyReturnRequestStatus


class PharmacyReturnRequest(Base):
    __tablename__ = "pharmacy_return_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    issue_voucher_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    issue_voucher_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    refill_request_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    store_unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    returning_unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    batch_number: Mapped[str] = mapped_column(String(80), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_issued_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_already_returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_issued_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[PharmacyReturnReasonCode] = mapped_column(
        Enum(PharmacyReturnReasonCode, name="pharmacy_return_reason_code"),
        nullable=False,
    )
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PharmacyReturnRequestStatus] = mapped_column(
        Enum(PharmacyReturnRequestStatus, name="pharmacy_return_request_status"),
        nullable=False,
        default=PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW,
        server_default=PharmacyReturnRequestStatus.RETURN_PENDING_STORE_REVIEW.value,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    receive_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_return_requests_id_clinic"),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_return_requests_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["issue_voucher_id"],
            ["pharmacy_issue_vouchers.id"],
            name="fk_pharmacy_return_requests_voucher",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["issue_voucher_item_id"],
            ["pharmacy_issue_voucher_items.id"],
            name="fk_pharmacy_return_requests_voucher_item",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["refill_request_id"],
            ["pharmacy_refill_requests.id"],
            name="fk_pharmacy_return_requests_refill_request",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["store_unit_id"],
            ["service_lines.id"],
            name="fk_pharmacy_return_requests_store_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["returning_unit_id"],
            ["service_lines.id"],
            name="fk_pharmacy_return_requests_returning_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["inventory_item_id"],
            ["pharmacy_inventory_items.id"],
            name="fk_pharmacy_return_requests_inventory_item",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_pharmacy_return_requests_requested_by",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_pharmacy_return_requests_reviewed_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["received_by"],
            ["users.id"],
            name="fk_pharmacy_return_requests_received_by",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "original_issued_quantity > 0",
            name="ck_pharmacy_return_requests_original_issued_positive",
        ),
        CheckConstraint(
            "quantity_requested > 0",
            name="ck_pharmacy_return_requests_requested_positive",
        ),
        CheckConstraint(
            "quantity_already_returned >= 0",
            name="ck_pharmacy_return_requests_already_returned_non_negative",
        ),
        CheckConstraint(
            "quantity_received >= 0 AND quantity_received <= quantity_requested",
            name="ck_pharmacy_return_requests_received_range",
        ),
        CheckConstraint(
            "remaining_issued_balance >= 0",
            name="ck_pharmacy_return_requests_remaining_non_negative",
        ),
        Index(
            "ix_pharmacy_return_requests_voucher_item_status",
            "issue_voucher_item_id",
            "status",
        ),
        Index(
            "ix_pharmacy_return_requests_returning_unit_status",
            "returning_unit_id",
            "status",
        ),
        Index(
            "ix_pharmacy_return_requests_store_unit_status",
            "store_unit_id",
            "status",
        ),
    )
