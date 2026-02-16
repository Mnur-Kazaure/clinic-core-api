import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKeyConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import DiagnosisMappingConfidence, DiagnosisSystem


class DiagnosisConditionMap(Base):
    __tablename__ = "diagnosis_condition_map"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    diagnosis_system: Mapped[DiagnosisSystem] = mapped_column(
        Enum(DiagnosisSystem, name="diagnosis_system"),
        nullable=False,
    )
    diagnosis_code: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_profile_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    confidence: Mapped[DiagnosisMappingConfidence] = mapped_column(
        Enum(DiagnosisMappingConfidence, name="diagnosis_mapping_confidence"),
        nullable=False,
        default=DiagnosisMappingConfidence.HIGH,
        server_default=DiagnosisMappingConfidence.HIGH.value,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_diagnosis_condition_map_clinic_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["condition_profile_id", "clinic_id"],
            ["condition_profiles.id", "condition_profiles.clinic_id"],
            name="fk_diagnosis_condition_map_condition_profile_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_diagnosis_condition_map_created_by",
        ),
        Index(
            "uq_diagnosis_condition_map_active",
            "clinic_id",
            "diagnosis_system",
            "diagnosis_code",
            unique=True,
            postgresql_where=text("active = true"),
            sqlite_where=text("active = 1"),
        ),
        Index(
            "ix_diagnosis_condition_map_clinic_lookup",
            "clinic_id",
            "diagnosis_system",
            "diagnosis_code",
        ),
    )
