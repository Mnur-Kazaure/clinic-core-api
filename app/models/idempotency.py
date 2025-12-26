# app/models/idempotency.py
import uuid
from sqlalchemy import Column, String, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    request_hash = Column(String, nullable=False)
    response_body = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)