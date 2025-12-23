# app/core/system_actor.py
from uuid import UUID
from app.shared.enums import UserRole


class SystemUser:
    """
    Internal system actor.
    Used only for automated lifecycle transitions.
    """

    id = UUID("00000000-0000-0000-0000-000000000001")
    role = UserRole.SYSTEM
    clinic_id = None  # validated explicitly where used