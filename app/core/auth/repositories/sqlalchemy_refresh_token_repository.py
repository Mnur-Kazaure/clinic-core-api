from datetime import datetime, timezone
from uuid import UUID
import hashlib
import secrets

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.auth.refresh_token_repository import RefreshTokenRepository
from app.models.refresh_token import RefreshToken


class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, db: Session):
        self.db = db

    # -----------------------
    # helpers
    # -----------------------
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate(self) -> str:
        return secrets.token_urlsafe(64)

    # -----------------------
    # contract implementation
    # -----------------------
    def issue(self, *, user_id: UUID, expires_at: datetime) -> str:
        raw = self._generate()
        token = RefreshToken(
            user_id=user_id,
            token_hash=self._hash(raw),
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()
        return raw

    def rotate(self, *, token: str, new_expires_at: datetime) -> tuple[str, UUID]:
        token_hash = self._hash(token)
        now = self._now()

        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )

        existing = self.db.execute(stmt).scalar_one_or_none()
        if not existing:
            raise ValueError("Invalid refresh token")

        if existing.revoked_at is not None or existing.expires_at <= now:
            raise ValueError("Refresh token revoked or expired")

        # revoke old
        existing.revoked_at = now
        existing.used_at = now

        # issue new
        new_raw = self._generate()
        replacement = RefreshToken(
            user_id=existing.user_id,
            token_hash=self._hash(new_raw),
            expires_at=new_expires_at,
        )

        self.db.add(replacement)
        self.db.commit()

        return new_raw, existing.user_id

    def revoke(self, *, token: str) -> None:
        token_hash = self._hash(token)

        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )

        existing = self.db.execute(stmt).scalar_one_or_none()
        if not existing:
            return

        existing.revoked_at = self._now()
        self.db.commit()

    def is_revoked(self, *, token: str) -> bool:
        token_hash = self._hash(token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        existing = self.db.execute(stmt).scalar_one_or_none()

        if not existing:
            return True

        return (
            existing.revoked_at is not None
            or existing.expires_at <= self._now()
        )

    # Admin helpers (post-MVP)
    def list_active(self, *, user_id: UUID):
        now = self._now()
        stmt = select(RefreshToken.id).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        return list(self.db.execute(stmt).scalars())

    def revoke_all(self, *, user_id: UUID) -> None:
        now = self._now()
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .with_for_update()
        )

        tokens = self.db.execute(stmt).scalars().all()
        for token in tokens:
            token.revoked_at = now

        self.db.commit()
# ------------------------------------------------

    def rotate_with_context(
        self,
        *,
        token: str,
        new_expires_at: datetime,
        device_id: str | None,
    ) -> tuple[str, UUID]:
        """
        MVP implementation:
        Device context is intentionally ignored.
        Delegates to rotate().
        """
        return self.rotate(
            token=token,
            new_expires_at=new_expires_at,
        )


    






# # app/core/auth/repositories/sqlalchemy_refresh_token_repository.py
# from datetime import datetime, timezone
# from uuid import UUID
# import hashlib
# import secrets

# from sqlalchemy.orm import Session
# from sqlalchemy import select
# from app.core.auth.refresh_token_repository import RefreshTokenRepository
# from app.models.refresh_token import RefreshToken


# class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
#     def __init__(self, db: Session):
#         self.db = db

#     # -----------------------
#     # internal helpers
#     # -----------------------
#     def _now(self) -> datetime:
#         return datetime.now(timezone.utc)

#     def _hash(self, token: str) -> str:
#         return hashlib.sha256(token.encode()).hexdigest()

#     def _generate(self) -> str:
#         return secrets.token_urlsafe(64)

#     def _is_invalid(self, token: RefreshToken) -> bool:
#         return (
#             token.revoked_at is not None
#             or token.expires_at <= self._now()
#         )

#     # -----------------------
#     # contract implementation
#     # -----------------------
#     def issue(self, *, user_id: UUID, expires_at: datetime) -> str:
#         raw = self._generate()
#         token = RefreshToken(
#             user_id=user_id,
#             token_hash=self._hash(raw),
#             expires_at=expires_at,
#         )
#         self.db.add(token)
#         self.db.commit()
#         return raw

#     def rotate(self, *, token: str, new_expires_at: datetime) -> str:
#         token_hash = self._hash(token)

#         stmt = (
#             select(RefreshToken)
#             .where(RefreshToken.token_hash == token_hash)
#             .with_for_update()
#         )

#         existing = self.db.execute(stmt).scalar_one_or_none()

#         if not existing:
#             raise ValueError("Invalid refresh token")

#         now = self._now()

#         # 🔒 EXPIRED
#         if existing.expires_at <= now:
#             raise ValueError("Refresh token expired")

#         # 🚨 REPLAY DETECTED
#         if existing.revoked and existing.replaced_by is not None:
#             # OPTIONAL: emit security log / metric here
#             raise ValueError("Refresh token reuse detected")

#         # 🔒 Normal revoked (logout case)
#         if existing.revoked:
#             raise ValueError("Refresh token revoked")

#         # 🔁 ROTATE
#         existing.revoked = True
#         existing.revoked_at = now

#         new_raw = self._generate_raw_token()
#         new_hash = self._hash(new_raw)

#         replacement = RefreshToken(
#             user_id=existing.user_id,
#             token_hash=new_hash,
#             expires_at=new_expires_at,
#             revoked=False,
#         )

#         self.db.add(replacement)
#         self.db.flush()  # obtain replacement.id

#         existing.replaced_by = replacement.id

#         self.db.commit()

#         return new_raw



#     def revoke(self, *, token: str) -> None:
#         token_hash = self._hash(token)

#         stmt = select(RefreshToken).where(
#             RefreshToken.token_hash == token_hash,
#             RefreshToken.revoked_at.is_(None),
#         )

#         existing = self.db.execute(stmt).scalar_one_or_none()
#         if not existing:
#             return

#         existing.revoked_at = self._now()
#         self.db.commit()

#     def is_revoked(self, *, token: str) -> bool:
#         token_hash = self._hash(token)

#         stmt = select(RefreshToken).where(
#             RefreshToken.token_hash == token_hash
#         )

#         existing = self.db.execute(stmt).scalar_one_or_none()
#         if not existing:
#             return True

#         return self._is_invalid(existing)
    
#     # List all active refresh token IDs for a user
#     def list_active(self, *, user_id: UUID) -> list[UUID]:
#         now = self._now()

#         stmt = select(RefreshToken.id).where(
#             RefreshToken.user_id == user_id,
#             RefreshToken.revoked.is_(False),
#             RefreshToken.expires_at > now,
#         )

#         return list(self.db.execute(stmt).scalars())
    
#     # 🔒 Global Logout (Revoke All)
#     def revoke_all(self, *, user_id: UUID) -> None:
#         now = self._now()

#         stmt = (
#             select(RefreshToken)
#             .where(
#                 RefreshToken.user_id == user_id,
#                 RefreshToken.revoked.is_(False),
#             )
#             .with_for_update()
#         )

#         tokens = self.db.execute(stmt).scalars().all()

#         for token in tokens:
#             token.revoked = True
#             token.revoked_at = now

#         self.db.commit()


#     # app/core/auth/repositories/sqlalchemy_refresh_token_repository.py

#     def rotate_with_context(
#         self,
#         *,
#         token: str,
#         new_expires_at: datetime,
#         device_id: str | None,
#     ) -> tuple[str, UUID]:  # Changed return type
#         token_hash = self._hash(token)
#         now = self._now()

#         stmt = (
#             select(RefreshToken)
#             .where(RefreshToken.token_hash == token_hash)
#             .with_for_update()
#         )

#         rt = self.db.execute(stmt).scalar_one_or_none()

#         if not rt or rt.revoked_at or rt.expires_at <= now:
#             raise ValueError("Invalid refresh token")

#         # Device binding
#         if rt.device_id and device_id and rt.device_id != device_id:
#             rt.revoked = True
#             rt.revoked_at = now
#             self.db.commit()
#             raise ValueError("Device mismatch")

#         if not rt.device_id and device_id:
#             rt.device_id = device_id

#         rt.last_used_at = now

#         # Standard rotation
#         rt.revoked = True
#         rt.revoked_at = now

#         new_raw = self._generate()
#         new_hash = self._hash(new_raw)

#         new_rt = RefreshToken(
#             user_id=rt.user_id,
#             token_hash=new_hash,
#             expires_at=new_expires_at,
#             device_id=rt.device_id,
#         )

#         self.db.add(new_rt)
#         self.db.commit()

#         return new_raw, rt.user_id  # Return both token and user_id
    