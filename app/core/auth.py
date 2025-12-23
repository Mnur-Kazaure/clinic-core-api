from fastapi import Depends
from app.core.config import settings

if settings.AUTH_MODE == "dev":
    from app.core.auth_dev import get_current_user
else:
    from app.core.auth_jwt import get_current_user  # future
