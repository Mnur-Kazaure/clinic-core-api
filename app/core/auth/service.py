# app/core/auth/service.py
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.auth.refresh_token_repository import RefreshTokenRepository
from app.core.config import settings


class AuthService:
    def __init__(self, refresh_token_repo: RefreshTokenRepository):
        self.refresh_token_repo = refresh_token_repo

    def _next_expiry(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            days=settings.AUTH_REFRESH_TOKEN_TTL_DAYS
        )

    def issue_refresh_token(self, user_id: UUID) -> str:
        expires_at = self._next_expiry()
        return self.refresh_token_repo.issue(
            user_id=user_id,
            expires_at=expires_at,
        )

    def refresh_access(self, *, refresh_token: str) -> tuple[str, UUID]:
        expires_at = self._next_expiry()
        return self.refresh_token_repo.rotate(
            token=refresh_token,
            new_expires_at=expires_at,
        )

    def revoke_refresh_token(self, refresh_token: str) -> None:
        self.refresh_token_repo.revoke(token=refresh_token)

    # Admin-only (post-MVP)
    def list_sessions(self, *, user_id: UUID):
        return self.refresh_token_repo.list_active(user_id=user_id)

    def global_logout(self, *, user_id: UUID) -> None:
        self.refresh_token_repo.revoke_all(user_id=user_id)






# # app/core/auth/service.py
# from datetime import datetime, timedelta, timezone
# from uuid import UUID
# # app/core/auth/refresh_token_repository.py
# from app.core.auth.refresh_token_repository import RefreshTokenRepository

# REFRESH_TOKEN_TTL_DAYS = 30


# class AuthService:
#     def __init__(self, refresh_token_repo: RefreshTokenRepository):
#         self.refresh_token_repo = refresh_token_repo

#     def issue_refresh_token(self, user_id: UUID) -> str:
#         expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
#         return self.refresh_token_repo.issue(
#             user_id=user_id,
#             expires_at=expires_at,
#         )
    
#     # app/core/auth/service.py

#     def rotate_refresh_token(self, refresh_token: str, device_id: str | None = None) -> tuple[str, UUID]:
#         new_expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
        
#         # Use new method if device_id provided, fallback to old
#         if device_id is not None:
#             new_token, user_id = self.refresh_token_repo.rotate_with_context(
#                 token=refresh_token,
#                 new_expires_at=new_expires_at,
#                 device_id=device_id,
#             )
#         else:
#             new_token, user_id = self.refresh_token_repo.rotate(
#                 token=refresh_token,
#                 new_expires_at=new_expires_at,
#             )
        
#         return new_token, user_id
    
    
#     def _next_expiry(self) -> datetime:
#         return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    

#     def refresh_access(self, *, refresh_token: str, device_id: str | None) -> str:
#         expires_at = self._next_expiry()
#         return self.refresh_token_repo.rotate_with_context(
#             token=refresh_token,
#             new_expires_at=expires_at,
#             device_id=device_id,
#         )



#     def revoke_refresh_token(self, refresh_token: str) -> None:
#         self.refresh_token_repo.revoke(token=refresh_token)
        
# # Admin note:

#     '''🌐 API (OPTIONAL, ADMIN-ONLY)
#         If exposed later:
#         /auth/sessions
#         /auth/logout-all

#         Must:
#         Require access token
#         Never accept refresh token input
#         Never leak token hashes
#         '''

#     def list_sessions(self, *, user_id: UUID) -> list[UUID]:            # /auth/sessions
#         return self.refresh_token_repo.list_active(user_id=user_id)
    
#     def global_logout(self, *, user_id: UUID) -> None:                # /auth/logout-all
#         self.refresh_token_repo.revoke_all(user_id=user_id)
