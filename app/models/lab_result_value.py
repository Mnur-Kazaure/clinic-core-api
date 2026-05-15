import uuid

from sqlalchemy import (
    Boolean,
    ForeignKeyConstraint,
    JSON,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LabResultValue(Base):
    __tablename__ = "lab_result_values"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    template_field_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    value_string: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    abnormal_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    critical_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["result_id"],
            ["lab_results.id"],
            name="fk_lab_result_values_result",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["template_field_id"],
            ["lab_result_template_fields.id"],
            name="fk_lab_result_values_template_field",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "result_id",
            "template_field_id",
            name="uq_lab_result_values_result_field",
        ),
    )
