"""Create the FIRST Admin account (order fix a in decisions.md).

Run from the backend folder:

    .venv\\Scripts\\python -m app.scripts.create_admin

It asks for the email and password (the password is not shown while you type).
For automated setups it can instead read ADMIN_EMAIL and ADMIN_PASSWORD from
environment variables. No password is ever written in the code, and the
password is never printed.

If an active Admin already exists, it does nothing. Further users are created
by that Admin through user management (Slice 1.6).
"""

import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models import Base  # noqa: F401  (loads every table)
from app.modules.users.models import Role, RoleName, User
from app.modules.users.service import create_user
from app.scripts._prompt import SeedSettings, ask_email, ask_password


def main() -> int:
    with SessionLocal() as db:
        existing = db.scalar(
            select(User).join(Role).where(Role.name == RoleName.ADMIN, User.is_active.is_(True))
        )
        if existing is not None:
            print(f"An active Admin already exists ({existing.email}). Nothing was created.")
            return 0

        seed = SeedSettings()
        if seed.admin_email and seed.admin_password:
            print("Using ADMIN_EMAIL and ADMIN_PASSWORD from the environment.")
            email, password = seed.admin_email, seed.admin_password
        else:
            print("Create the first Admin account.")
            email = seed.admin_email or ask_email("Admin email: ")
            password = ask_password()

        try:
            user = create_user(db, email=email, password=password, role_name=RoleName.ADMIN)
        except AppError as exc:
            print(f"Not created: {exc.message}", file=sys.stderr)
            return 1

    print(f"Admin account created: {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
