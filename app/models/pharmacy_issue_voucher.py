import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PharmacyIssueVoucherStatus


class PharmacyIssueVoucher(Base):
    __tablename__ = "pharmacy_issue_vouchers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    voucher_number: Mapped[str] = mapped_column(String(64), nullable=False)
    store_unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    receiving_unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    refill_request_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[PharmacyIssueVoucherStatus] = mapped_column(
        Enum(PharmacyIssueVoucherStatus, name="pharmacy_issue_voucher_status"),
        nullable=False,
        default=PharmacyIssueVoucherStatus.PREPARED,
        server_default=PharmacyIssueVoucherStatus.PREPARED.value,
    )
    prepared_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    issued_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dispatched_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_pharmacy_issue_vouchers_id_clinic"),
        UniqueConstraint(
            "clinic_id",
            "voucher_number",
            name="uq_pharmacy_issue_vouchers_clinic_number",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_pharmacy_issue_vouchers_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["store_unit_id"],
            ["service_lines.id"],
            name="fk_pharmacy_issue_vouchers_store_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["receiving_unit_id"],
            ["service_lines.id"],
            name="fk_pharmacy_issue_vouchers_receiving_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["refill_request_id"],
            ["pharmacy_refill_requests.id"],
            name="fk_pharmacy_issue_vouchers_refill_request",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["prepared_by"],
            ["users.id"],
            name="fk_pharmacy_issue_vouchers_prepared_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_pharmacy_issue_vouchers_approved_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["issued_by"],
            ["users.id"],
            name="fk_pharmacy_issue_vouchers_issued_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["dispatched_by"],
            ["users.id"],
            name="fk_pharmacy_issue_vouchers_dispatched_by",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
            name="fk_pharmacy_issue_vouchers_acknowledged_by",
            ondelete="SET NULL",
        ),
    )
