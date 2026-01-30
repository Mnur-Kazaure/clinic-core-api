# app/core/auth/dependencies.py
from fastapi import Cookie, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth.jwt import decode_access_token
from app.core.auth.context_db import DbAuthContext

ACCESS_COOKIE = "access_token"


def get_current_user(
    access_token: str | None = Cookie(default=None, alias=ACCESS_COOKIE),
    db: Session = Depends(get_db),
):
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        claims = decode_access_token(access_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    context = DbAuthContext(db)
    return context.resolve_user(claims)





# # app/core/auth/dependencies.py
# from fastapi import Header, HTTPException, status, Depends
# from sqlalchemy.orm import Session

# from app.core.database import get_db
# from app.core.auth.jwt import decode_access_token
# from app.core.auth.context_db import DbAuthContext


# def get_current_user(
#     authorization: str | None = Header(default=None),
#     db: Session = Depends(get_db),
# ):
#     """
#     Composition root for authentication.

#     Responsibilities:
#     - Extract Bearer token
#     - Decode JWT
#     - Instantiate AuthContext with DB
#     - Resolve and return User

#     This is the ONLY place where:
#     - DB enters auth
#     - Context is constructed
#     """

#     if not authorization:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authorization header missing",
#         )

#     if not authorization.startswith("Bearer "):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid Authorization header format",
#         )

#     token = authorization.removeprefix("Bearer ").strip()

#     try:
#         claims = decode_access_token(token)
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid or expired token",
#         )

#     context = DbAuthContext(db)
#     return context.resolve_user(claims)