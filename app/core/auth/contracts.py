from typing import Protocol
from app.models.user import User


class AuthContext(Protocol):
    """
    Auth Context contract.

    Responsibility:
    - Resolve a User from validated JWT claims

    Constraints:
    - No DB creation
    - No FastAPI dependencies
    - No side effects
    """

    def resolve_user(self, claims: dict) -> User:
        ...
