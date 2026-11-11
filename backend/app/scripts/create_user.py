"""DEVELOPMENT ONLY: create a test login with any role.

Until user management exists (Slice 1.6) this is how you make an IT Manager
or Employee account to try the role checks. It refuses to run when
APP_ENV=production.

    .venv\\Scripts\\python -m app.scripts.create_user --role Employee
    .venv\\Scripts\\python -m app.scripts.create_user --role "IT Manager" --email it@example.com

The password is always asked for (never typed on the command line, where it
would be saved in your command history).
"""

import argparse
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models import Base  # noqa: F401  (loads every table)
from app.modules.users.models import RoleName
from app.modules.users.service import create_user
from app.scripts._prompt import ask_email, ask_password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a development test user.")
    parser.add_argument("--role", required=True, choices=RoleName.ALL)
    parser.add_argument("--email")
    args = parser.parse_args(argv)

    if get_settings().is_production:
        print("create_user is for development only. Use user management instead.", file=sys.stderr)
        return 1

    email = args.email or ask_email()
    password = ask_password()
    with SessionLocal() as db:
        try:
            user = create_user(db, email=email, password=password, role_name=args.role)
        except AppError as exc:
            print(f"Not created: {exc.message}", file=sys.stderr)
            return 1
    print(f"{args.role} account created: {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
