# app/core/idempotency.py
import hashlib
import json
from fastapi import Depends, Header, HTTPException, status
from app.core.database import get_db
from app.models.idempotency import IdempotencyKey


def hash_request(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def idempotent(endpoint: str):
    def dependency(
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        db=Depends(get_db),
    ):
        record = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.key == idempotency_key,
                IdempotencyKey.endpoint == endpoint,
            )
            .first()
        )

        return record, idempotency_key, db

    return dependency
