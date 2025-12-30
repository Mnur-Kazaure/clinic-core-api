# app/services/auth/refresh_token_service.py

import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

from app.models.refresh_token import RefreshToken


REFRESH_TOKEN_TTL_DAYS = 30


class RefreshTokenService:
    def __init__(self, db: Session):
        self.db = db

    # 🔐 INTERNAL — never expose hash logic outside this service
    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    # 1️⃣ Issue new refresh token (login, password grant)
    def issue_token(
        self,
        *,
        user_id: UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> str:
        raw_token = secrets.token_urlsafe(64)
        token_hash = self._hash_token(raw_token)

        refresh_token = RefreshToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self.db.add(refresh_token)
        self.db.commit()

        return raw_token  # returned once, never stored

    # 2️⃣ Rotate refresh token (refresh flow)
    def rotate_token(self, raw_token: str) -> str:
        token_hash = self._hash_token(raw_token)

        token = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .with_for_update()
            .first()
        )

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if token.revoked_at or token.expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or revoked",
            )

        # 🔁 Issue replacement token
        new_raw = secrets.token_urlsafe(64)
        new_hash = self._hash_token(new_raw)

        replacement = RefreshToken(
            id=uuid4(),
            user_id=token.user_id,
            token_hash=new_hash,
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
            user_agent=token.user_agent,
            ip_address=token.ip_address,
        )

        # 🔒 Revoke old token
        token.revoked_at = datetime.utcnow()
        token.replaced_by = replacement.id

        self.db.add(replacement)
        self.db.commit()

        return new_raw

    # 3️⃣ Revoke refresh token (logout)
    def revoke_token(self, raw_token: str) -> None:
        token_hash = self._hash_token(raw_token)

        token = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .with_for_update()
            .first()
        )

        if not token:
            return  # idempotent logout

        if token.revoked_at:
            return

        token.revoked_at = datetime.utcnow()
        self.db.commit()