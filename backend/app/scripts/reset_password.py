"""DEVELOPMENT ONLY: give an existing login a new password.

The app has no "forgot / reset password" feature yet (open item R2), and
create_admin does nothing once an active Admin exists. This script fills that
gap on a developer's own machine, e.g. when the dev Admin's password is lost:

    .venv\\Scripts\\python -m app.scripts.reset_password --email admin@example.com

- It runs ONLY when APP_ENV is explicitly set to "development" (in backend\\.env or
  the environment). It refuses APP_ENV=production, APP_ENV=test, and an APP_ENV
  that is not set at all (the app's default is "development", so a server that
  forgot to set APP_ENV must not be treated as a developer's machine). Decision D8.
- The new password is always asked for, twice, without showing it (never typed
  on the command line, where it would be saved in your command history), and
  must meet PASSWORD_MIN_LENGTH. It is stored only as a one-way hash.
- Only the password changes: role, status and employee link stay as they are.
  A deactivated login stays deactivated (activate it on the Users page).
- An audit row `user.updated` is written in the same transaction, recorded as a
  system action with no actor (as the seed scripts, B11). The password itself is
  never written to the audit log or printed.
"""

import argparse
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.core.security import hash_password
from app.models import Base  # noqa: F401  (loads every table)
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.users.service import get_user_by_email, validate_new_password
from app.scripts._prompt import ask_email, ask_password

AUDIT_NOTE = "password reset with the development script"


def development_only_refusal(settings) -> str | None:
    """Why the script must not run here, or None when APP_ENV=development was set on purpose."""
    explicitly_set = "app_env" in getattr(settings, "model_fields_set", set())
    if settings.app_env == "development" and explicitly_set:
        return None
    shown = settings.app_env if explicitly_set else "not set"
    return (
        f"reset_password is for development only (APP_ENV is {shown}). "
        "It runs only when APP_ENV=development is set in backend\\.env or the environment."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Development only: set a new password for an existing login.")
    parser.add_argument("--email", help="The login's email (asked for when left out).")
    args = parser.parse_args(argv)

    refusal = development_only_refusal(get_settings())
    if refusal:
        print(refusal, file=sys.stderr)
        return 1

    with SessionLocal() as db:
        email = args.email or ask_email()
        user = get_user_by_email(db, email)
        if user is None:
            print(f"Not changed: no login with the email {email.strip().lower()}.", file=sys.stderr)
            return 1

        password = ask_password()
        try:
            validate_new_password(password)
        except AppError as exc:
            print(f"Not changed: {exc.message}", file=sys.stderr)
            return 1

        try:
            user.password_hash = hash_password(password)
            audit.record(
                db,
                actor=None,  # a system action (no one is logged in)
                action=AuditAction.USER_UPDATED,
                entity=user,
                before={"change": None},
                after={"change": AUDIT_NOTE},
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        print(f"New password set for {user.email} ({user.role.name}).")
        if not user.is_active:
            print("Note: this login is deactivated. An Admin must activate it on the Users page before it can sign in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
