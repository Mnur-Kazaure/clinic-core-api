from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from uuid import UUID

import jwt
from jwt import PyJWTError

from app.core.auth.settings import auth_settings
from app.shared.enums import UserRole


def encode_access_token(
    *,
    user_id: UUID,
    role: UserRole,
    clinic_id: UUID,
) -> str:
    now = datetime.now(tz=timezone.utc)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "clinic_id": str(clinic_id),
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=auth_settings.JWT_ACCESS_TOKEN_TTL_SECONDS)).timestamp()
        ),
    }

    return jwt.encode(
        payload,
        auth_settings.JWT_SECRET_KEY,
        algorithm=auth_settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            auth_settings.JWT_SECRET_KEY,
            algorithms=[auth_settings.JWT_ALGORITHM],
        )
        return payload

    except PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc