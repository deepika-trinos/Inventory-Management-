"""Login, current user and logout endpoints: /api/v1/auth/..."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and get an access token",
    responses={
        **error_responses(401, 422),
        403: {**error_responses(403)[403], "description": "Account is deactivated"},
    },
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Check email + password and return a JWT access token.

    - Email is not case-sensitive.
    - Wrong email and wrong password give the **same** error (`invalid_credentials`),
      so nobody can find out which emails have accounts.
    - A deactivated account gets `account_inactive` (only after a correct password).

    Use the token as `Authorization: Bearer <access_token>`. In /docs: click
    **Authorize** and paste the token.
    """
    token, expires_in = service.login(db, body.email, body.password)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Who am I?",
    responses=error_responses(401),
)
def me(user: User = Depends(get_current_user)) -> User:
    """Return the logged-in user, their role and linked employee (if any).

    Never includes the password hash. Times are in UTC.
    """
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    responses=error_responses(401),
)
def logout(_: User = Depends(get_current_user)) -> Response:
    """Log out.

    **How logout works with JWT:** the server does not keep a list of logged-in
    sessions; the token itself proves who you are until it expires. So logout means:

    1. The frontend **deletes its copy of the token** (this is what actually logs you out).
    2. Tokens are **short-lived** (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30), so a
       copied token stops working soon anyway.
    3. If an Admin **deactivates** a user, all of that user's tokens stop working on the
       very next request, because every request re-checks the user in the database.

    This endpoint exists so the frontend has one clear "log out" call (and so a
    future version could record logouts or block tokens without frontend changes).
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)
