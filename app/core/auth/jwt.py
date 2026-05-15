# app/core/auth/jwt.py
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from uuid import UUID

import jwt
from jwt import PyJWTError

from app.core.config import settings
from app.shared.enums import UserRole


def encode_access_token(
    *,
    user_id: UUID,
    role: UserRole,
    clinic_id: UUID,
    current_department_id: UUID | None = None,
    allowed_department_ids: list[UUID] | None = None,
) -> str:
    now = datetime.now(tz=timezone.utc)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "clinic_id": str(clinic_id),
        "current_department_id": (
            str(current_department_id) if current_department_id is not None else None
        ),
        "allowed_department_ids": [
            str(department_id)
            for department_id in (allowed_department_ids or [])
        ],
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.AUTH_JWT_ACCESS_TOKEN_TTL_SECONDS)).timestamp()
        ),
    }

    return jwt.encode(
        payload,
        settings.AUTH_JWT_SECRET_KEY,
        algorithm=settings.AUTH_JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_JWT_SECRET_KEY,
            algorithms=[settings.AUTH_JWT_ALGORITHM],
        )
        return payload

    except PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc
