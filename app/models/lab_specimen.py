import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
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
from app.shared.enums import LabSpecimenRejectionReasonCode, LabSpecimenStatus


class LabSpecimen(Base):
    __tablename__ = "lab_specimens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    accession_number: Mapped[str] = mapped_column(String(32), nullable=False)
    request_item_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    target_unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    specimen_type: Mapped[str] = mapped_column(String(80), nullable=False)
    specimen_source: Mapped[str] = mapped_column(String(80), nullable=False)
    container_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    collection_site: Mapped[str | None] = mapped_column(String(80), nullable=True)
    specimen_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    specimen_label_suffix: Mapped[str | None] = mapped_column(String(16), nullable=True)
    collected_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[LabSpecimenStatus] = mapped_column(
        Enum(LabSpecimenStatus, name="lab_specimen_status"),
        nullable=False,
        default=LabSpecimenStatus.PENDING_COLLECTION,
        server_default=LabSpecimenStatus.PENDING_COLLECTION.value,
    )
    rejection_reason_code: Mapped[LabSpecimenRejectionReasonCode | None] = mapped_column(
        Enum(
            LabSpecimenRejectionReasonCode,
            name="lab_specimen_rejection_reason_code",
        ),
        nullable=True,
    )
    rejection_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_specimens_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["request_item_id"],
            ["lab_requests.id"],
            name="fk_lab_specimens_request_item",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["target_unit_id"],
            ["service_lines.id"],
            name="fk_lab_specimens_target_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["collected_by"],
            ["users.id"],
            name="fk_lab_specimens_collected_by",
        ),
        ForeignKeyConstraint(
            ["received_by"],
            ["users.id"],
            name="fk_lab_specimens_received_by",
        ),
        ForeignKeyConstraint(
            ["rejected_by"],
            ["users.id"],
            name="fk_lab_specimens_rejected_by",
        ),
        UniqueConstraint("accession_number", name="uq_lab_specimens_accession"),
        UniqueConstraint(
            "request_item_id",
            "specimen_sequence",
            name="uq_lab_specimens_request_sequence",
        ),
        CheckConstraint(
            "specimen_sequence >= 1",
            name="ck_lab_specimens_sequence_positive",
        ),
        Index(
            "ix_lab_specimens_clinic_status_unit",
            "clinic_id",
            "status",
            "target_unit_id",
        ),
    )
