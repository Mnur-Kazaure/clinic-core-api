# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from app.core.config import settings
import datetime
from app.core.database import get_db
from app.core.auth.passwords import verify_password
from app.core.auth.jwt import encode_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.core.auth import get_current_user
from app.services.event_service import EventService
from app.core.auth.service import AuthService
from app.core.auth.repositories.sqlalchemy_refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.schemas.auth import MeResponse
from app.shared.enums import UserRole



router = APIRouter(prefix="/auth", tags=["Auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    repo = SqlAlchemyRefreshTokenRepository(db)
    return AuthService(repo)




# Add these imports at the top


# Token expiry settings
ACCESS_TOKEN_EXPIRE_MINUTES = settings.AUTH_JWT_ACCESS_TOKEN_TTL_SECONDS // 60
REFRESH_TOKEN_EXPIRE_DAYS = settings.AUTH_REFRESH_TOKEN_TTL_DAYS
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"

@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            EventService(db).emit(
                event_type="LOGIN_FAILED",
                actor_id=user.id,
                actor_role=user.role,
                clinic_id=user.clinic_id,
                patient_id=None,
                emitter="auth",
                payload={
                    "reason": "invalid_credentials",
                },
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = encode_access_token(
        user_id=user.id,
        role=UserRole(user.role),
        clinic_id=user.clinic_id,
    )

    refresh_token = auth_service.issue_refresh_token(user.id)

    # 🚨 CRITICAL FIX: Add max_age and secure settings
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=False,  # True in production, False for localhost
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 🚨 ADD THIS
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=False,  # True in production, False for localhost  
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # 🚨 ADD THIS
    )

    return {"detail": "Login successful"}

@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        new_refresh_token, user_id = auth_service.refresh_access(
            refresh_token=refresh_token
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    access_token = encode_access_token(
        user_id=user.id,
        role=UserRole(user.role),
        clinic_id=user.clinic_id,
    )

    # 🚨 CRITICAL FIX: Add max_age here too
    response.set_cookie(
        key=ACCESS_COOKIE, 
        value=access_token, 
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key=REFRESH_COOKIE, 
        value=new_refresh_token, 
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    return {"detail": "Token refreshed"}



@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if refresh_token:
        auth_service.revoke_refresh_token(refresh_token)

    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)

    return {"detail": "Logged out"}


# api/v1/auth.py
@router.get("/me", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user)):
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user
