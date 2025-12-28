from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth.passwords import verify_password
from app.core.auth.jwt import encode_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and mint access token.
    """
    user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if not user or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = encode_access_token(
        user_id=user.id,
        role=user.role,
        clinic_id=user.clinic_id,
    )


    return TokenResponse(access_token=access_token)