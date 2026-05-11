import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DoctorServiceLine(Base):
    __tablename__ = "doctor_service_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    service_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_lines.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "service_line_id",
            name="uq_doctor_service_lines_doctor_service_line",
        ),
    )
