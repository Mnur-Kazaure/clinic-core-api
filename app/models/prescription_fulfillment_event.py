# app/models/prescription_fulfillment_event.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import PrescriptionFulfillmentType


class PrescriptionFulfillmentEvent(Base):
    """
    Append-only fulfillment facts for prescriptions.

    This lets Pharmacy record "dispensed in-house" vs "dispensed externally"
    without mutating the prescription row. Visit completion logic can derive
    "pharmacy done" from these events.
    """

    __tablename__ = "prescription_fulfillment_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )

    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fulfillment_type: Mapped[PrescriptionFulfillmentType] = mapped_column(
        Enum(PrescriptionFulfillmentType, name="prescription_fulfillment_type"),
        nullable=False,
    )

    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        # v1: we treat fulfillment as a single terminal fact per prescription.
        UniqueConstraint(
            "clinic_id",
            "prescription_id",
            name="uq_prescription_fulfillment_events_prescription",
        ),
    )

