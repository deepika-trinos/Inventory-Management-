"""Login logic."""

from sqlalchemy.orm import Session

from app.core.database import utc_now
from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.modules.users.models import User
from app.modules.users.service import get_user_by_email

def _invalid_credentials() -> AppError:
    # One message for "no such email" AND "wrong password", so the login form
    # never reveals which email addresses have accounts.
    return AppError(401, "invalid_credentials", "Incorrect email or password.")


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    is_valid, new_hash = verify_password(password, user.password_hash if user else None)
    if user is None or not is_valid:
        raise _invalid_credentials()

    # The password was right, so telling this person the account is
    # deactivated reveals nothing they could not already know.
    if not user.is_active:
        raise AppError(
            403, "account_inactive", "This account is deactivated. Please contact an administrator."
        )

    if new_hash:  # stored hash used older settings: upgrade it quietly
        user.password_hash = new_hash
    user.last_login_at = utc_now()
    db.commit()
    return user


def login(db: Session, email: str, password: str) -> tuple[str, int]:
    user = authenticate(db, email, password)
    return create_access_token(user.id)
