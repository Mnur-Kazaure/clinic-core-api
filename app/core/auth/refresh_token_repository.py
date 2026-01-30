# app/core/auth/contracts/refresh_token_repository.py

from abc import ABC, abstractmethod
from uuid import UUID
from datetime import datetime


class RefreshTokenRepository(ABC):
    """
    Domain contract for refresh token persistence and lifecycle.

    Responsibilities:
    - Issue refresh tokens
    - Rotate refresh tokens
    - Revoke refresh tokens
    - Enforce single-use & expiration

    This interface is:
    - Storage-agnostic
    - Framework-agnostic
    - Request-agnostic

    It MUST NOT be used in request-time auth resolution.
    """

    @abstractmethod
    def issue(self, *, user_id: UUID, expires_at: datetime) -> str:
        """
        Create and persist a new refresh token.

        Returns:
            raw_refresh_token (str): The plaintext token returned to the client.
        """
        raise NotImplementedError

    @abstractmethod
    def rotate(self, *, token: str, new_expires_at: datetime) -> str:
        """
        Atomically rotate a refresh token.

        Rules:
        - Old token must be valid and unrevoked
        - Old token must be revoked after rotation
        - Reuse of old token MUST fail

        Returns:
            new_raw_refresh_token (str)
        """
        raise NotImplementedError

    @abstractmethod
    def revoke(self, *, token: str) -> None:
        """
        Revoke a refresh token explicitly (logout, admin action, breach response).
        """
        raise NotImplementedError

    @abstractmethod
    def is_revoked(self, *, token: str) -> bool:
        """
        Check whether a refresh token has been revoked or expired.

        Intended for defensive checks inside auth flows only.
        """
        raise NotImplementedError
    

    @abstractmethod
    def rotate_with_context(
        self,
        *,
        token: str,
        new_expires_at: datetime,
        device_id: str | None,
    ) -> tuple[str, UUID]:  # Must match
        """Rotate with device context validation."""