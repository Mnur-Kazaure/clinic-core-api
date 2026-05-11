# app/core/auth/dependencies.py
from uuid import UUID

from fastapi import Cookie, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth.jwt import decode_access_token
from app.core.auth.context_db import DbAuthContext
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.department_mapping_service import DepartmentMappingService
from app.services.lab_unit_access_service import LabUnitAccessService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService

ACCESS_COOKIE = "access_token"


def get_current_user(
    access_token: str | None = Cookie(default=None, alias=ACCESS_COOKIE),
    x_department_id: str | None = Header(default=None, alias="X-Department-ID"),
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
    user = context.resolve_user(claims)

    mapping_service = DepartmentMappingService(db)
    db_allowed = mapping_service.user_allowed_department_ids(
        clinic_id=user.clinic_id,
        user_id=user.id,
    )
    db_primary = mapping_service.user_primary_department_id(
        clinic_id=user.clinic_id,
        user_id=user.id,
    )

    claimed_allowed_raw = claims.get("allowed_department_ids") or []
    claimed_allowed: list[UUID] = []
    for value in claimed_allowed_raw:
        try:
            claimed_allowed.append(UUID(str(value)))
        except Exception:
            continue

    allowed_department_ids = db_allowed or claimed_allowed

    requested_department_id: UUID | None = None
    if x_department_id:
        try:
            requested_department_id = UUID(x_department_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid X-Department-ID header",
            )
        if requested_department_id not in allowed_department_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department access denied",
            )

    claimed_current_raw = claims.get("current_department_id")
    claimed_current: UUID | None = None
    if claimed_current_raw:
        try:
            claimed_current = UUID(str(claimed_current_raw))
        except Exception:
            claimed_current = None

    resolved_current = (
        requested_department_id
        or db_primary
        or claimed_current
        or (allowed_department_ids[0] if allowed_department_ids else None)
    )

    department_context = mapping_service.user_department_context(
        clinic_id=user.clinic_id,
        user_id=user.id,
    )
    current_department_name = None
    for item in department_context:
        if item["id"] == resolved_current:
            current_department_name = item["name"]
            break

    setattr(user, "current_department_id", resolved_current)
    setattr(user, "allowed_department_ids", allowed_department_ids)
    setattr(user, "allowed_departments", department_context)
    setattr(user, "current_department_name", current_department_name)
    lab_unit_service = LabUnitAccessService(db)
    default_lab_unit_id, allowed_lab_unit_ids, allowed_lab_units = lab_unit_service.context_for_user(
        clinic_id=user.clinic_id,
        user=user,
    )
    setattr(user, "default_lab_unit_id", default_lab_unit_id)
    setattr(user, "allowed_lab_unit_ids", allowed_lab_unit_ids)
    setattr(user, "allowed_lab_units", allowed_lab_units)
    pharmacy_unit_service = PharmacyUnitAccessService(db)
    (
        default_pharmacy_unit_id,
        allowed_pharmacy_unit_ids,
        allowed_pharmacy_units,
    ) = pharmacy_unit_service.context_for_user(
        clinic_id=user.clinic_id,
        user=user,
    )
    setattr(user, "default_pharmacy_unit_id", default_pharmacy_unit_id)
    setattr(user, "allowed_pharmacy_unit_ids", allowed_pharmacy_unit_ids)
    setattr(user, "allowed_pharmacy_units", allowed_pharmacy_units)
    cashier_pay_point_service = CashierPayPointAccessService(db)
    (
        default_cashier_pay_point_id,
        allowed_cashier_pay_point_ids,
        allowed_cashier_pay_points,
    ) = cashier_pay_point_service.context_for_user(
        clinic_id=user.clinic_id,
        user=user,
    )
    setattr(user, "default_cashier_pay_point_id", default_cashier_pay_point_id)
    setattr(user, "allowed_cashier_pay_point_ids", allowed_cashier_pay_point_ids)
    setattr(user, "allowed_cashier_pay_points", allowed_cashier_pay_points)
    return user





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
