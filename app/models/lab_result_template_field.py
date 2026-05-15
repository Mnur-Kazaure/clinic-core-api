import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKeyConstraint,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabResultFieldType


class LabResultTemplateField(Base):
    __tablename__ = "lab_result_template_fields"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    field_code: Mapped[str] = mapped_column(String(64), nullable=False)
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[LabResultFieldType] = mapped_column(
        Enum(LabResultFieldType, name="lab_result_field_type"),
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_range_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_min: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    reference_max: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    reference_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    options_json: Mapped[list[str] | dict | None] = mapped_column(JSON, nullable=True)
    critical_rules_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    validation_rules_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["template_id"],
            ["lab_result_templates.id"],
            name="fk_lab_result_template_fields_template",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "template_id",
            "field_code",
            name="uq_lab_result_template_fields_template_code",
        ),
        CheckConstraint(
            "display_order >= 1",
            name="ck_lab_result_template_fields_display_order",
        ),
    )
