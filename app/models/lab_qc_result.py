import uuid

from sqlalchemy import Enum, ForeignKeyConstraint, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.shared.enums import LabQcStatus


class LabQcResult(Base):
    __tablename__ = "lab_qc_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    qc_run_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    analyte_name: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_min: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    expected_max: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    observed_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    status: Mapped[LabQcStatus] = mapped_column(
        Enum(LabQcStatus, name="lab_qc_status"),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["qc_run_id"],
            ["lab_qc_runs.id"],
            name="fk_lab_qc_results_run",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "qc_run_id",
            "analyte_name",
            name="uq_lab_qc_results_run_analyte",
        ),
    )
