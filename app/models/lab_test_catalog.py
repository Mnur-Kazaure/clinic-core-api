import uuid

from sqlalchemy import (
    Boolean,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LabTestCatalog(Base):
    __tablename__ = "lab_test_catalog"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    test_code: Mapped[str] = mapped_column(String(64), nullable=False)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    specimen_type: Mapped[str] = mapped_column(String(80), nullable=False)
    default_template_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_test_catalog_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["unit_id"],
            ["service_lines.id"],
            name="fk_lab_test_catalog_unit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["default_template_id"],
            ["lab_result_templates.id"],
            name="fk_lab_test_catalog_default_template",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("clinic_id", "test_code", name="uq_lab_test_catalog_clinic_code"),
        UniqueConstraint("clinic_id", "test_name", name="uq_lab_test_catalog_clinic_name"),
        Index("ix_lab_test_catalog_clinic_unit", "clinic_id", "unit_id"),
        Index("ix_lab_test_catalog_clinic_name", "clinic_id", "test_name"),
    )
