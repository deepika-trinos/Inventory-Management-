"""Reusable checks that protect endpoints.

A FastAPI "dependency" is a function FastAPI runs BEFORE your endpoint. If it
raises an error, the endpoint never runs. You attach it like this:

    @router.get("/something")
    def something(user: User = Depends(get_current_user)):            # any logged-in user
        ...

    @router.post("/something-else")
    def something_else(user: User = Depends(require_roles(RoleName.ADMIN, RoleName.IT_MANAGER))):
        ...

Every protected endpoint MUST use one of these. Hiding buttons in the
frontend is not security; these server-side checks are (PRD section 4).
"""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import TokenError, decode_access_token
from app.modules.users.models import RoleName, User

# Reads "Authorization: Bearer <token>". Also adds the "Authorize" button to /docs.
_bearer = HTTPBearer(
    auto_error=False,
    description="Paste the access_token from POST /api/v1/auth/login.",
)

_WWW_AUTH = {"WWW-Authenticate": "Bearer"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Who is calling? Runs on every protected request.

    1. A token must be present.
    2. Its signature and expiry must be valid.
    3. The user must STILL exist and be active in the database right now.
       Step 3 is why a deactivated user's old token stops working immediately,
       and why a role change takes effect on the very next request.
    """
    if credentials is None:
        raise AppError(401, "not_authenticated", "You must be logged in.", headers=_WWW_AUTH)

    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenError:
        raise AppError(
            401, "invalid_token", "Your session is invalid or has expired. Please log in again.",
            headers=_WWW_AUTH,
        ) from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(
            401, "invalid_token", "Your session is invalid or has expired. Please log in again.",
            headers=_WWW_AUTH,
        )
    return user


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    """Only let users with one of these roles through. Everyone else gets 403."""
    unknown = set(allowed_roles) - set(RoleName.ALL)
    if not allowed_roles or unknown:
        # Catches typos like "admin" when the code starts, not in production.
        raise ValueError(f"require_roles: unknown role(s) {sorted(unknown)}")

    def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in allowed_roles:
            raise AppError(
                403,
                "forbidden",
                "You do not have permission to do this.",
                {"your_role": user.role.name, "allowed_roles": list(allowed_roles)},
            )
        return user

    return _check_role
