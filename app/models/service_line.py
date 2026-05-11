import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import ServiceLineKind


class ServiceLine(Base):
    __tablename__ = "service_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    default_child_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    requires_doctor: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    service_line_kind: Mapped[ServiceLineKind] = mapped_column(
        Enum(ServiceLineKind, name="service_line_kind"),
        nullable=False,
        default=ServiceLineKind.GENERAL,
        server_default=ServiceLineKind.GENERAL.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "clinic_id", name="uq_service_lines_id_clinic"),
        UniqueConstraint(
            "clinic_id",
            "name",
            "parent_id",
            name="uq_service_lines_clinic_name_parent",
        ),
        CheckConstraint("(parent_id IS NULL) OR (parent_id != id)", name="ck_service_lines_parent_self"),
        CheckConstraint(
            "(default_child_id IS NULL) OR (default_child_id != id)",
            name="ck_service_lines_default_child_self",
        ),
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_service_lines_clinic_id",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["parent_id"],
            ["service_lines.id"],
            name="fk_service_lines_parent_id",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["default_child_id"],
            ["service_lines.id"],
            name="fk_service_lines_default_child_id",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_service_lines_department_id",
            ondelete="SET NULL",
        ),
    )
