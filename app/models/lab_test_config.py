import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabVerificationPolicy


class LabTestConfig(Base):
    __tablename__ = "lab_test_config"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    catalog_test_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="NGN",
        server_default="NGN",
    )
    turnaround_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    billing_name: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_policy: Mapped[LabVerificationPolicy] = mapped_column(
        Enum(LabVerificationPolicy, name="lab_verification_policy"),
        nullable=False,
        default=LabVerificationPolicy.OPTIONAL,
        server_default=LabVerificationPolicy.OPTIONAL.value,
    )
    allows_scientist_verification: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    scientist_verification_restricted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    critical_rules_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            name="fk_lab_test_config_clinic",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["catalog_test_id"],
            ["lab_test_catalog.id"],
            name="fk_lab_test_config_catalog_test",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["unit_id"],
            ["service_lines.id"],
            name="fk_lab_test_config_unit",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "clinic_id",
            "catalog_test_id",
            name="uq_lab_test_config_clinic_catalog_test",
        ),
        CheckConstraint(
            "price_minor >= 0",
            name="ck_lab_test_config_price_non_negative",
        ),
        CheckConstraint(
            "turnaround_time_minutes >= 0",
            name="ck_lab_test_config_turnaround_non_negative",
        ),
        CheckConstraint(
            "display_order >= 1",
            name="ck_lab_test_config_display_order_positive",
        ),
        Index(
            "ix_lab_test_config_clinic_unit_display",
            "clinic_id",
            "unit_id",
            "display_order",
        ),
    )
