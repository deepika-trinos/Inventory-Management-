"""DEVELOPMENT ONLY: create a test login with any role.

Until user management exists (Slice 1.6) this is how you make an IT Manager
or Employee account to try the role checks. It refuses to run when
APP_ENV=production.

    .venv\\Scripts\\python -m app.scripts.create_user --role "IT Manager" --email it@example.com
    .venv\\Scripts\\python -m app.scripts.create_user --role Employee --employee-code EMP-001

Since Slice 2.2 an Employee-role login must be linked to an existing, active
employee record without a login (order fix b): give its employee ID with
--employee-code (create the employee on the Employees page first).

The password is always asked for (never typed on the command line, where it
would be saved in your command history).
"""

import argparse
import sys

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models import Base  # noqa: F401  (loads every table)
from app.modules.employees.models import Employee
from app.modules.users.models import RoleName
from app.modules.users.service import create_user
from app.scripts._prompt import ask_email, ask_password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a development test user.")
    parser.add_argument("--role", required=True, choices=RoleName.ALL)
    parser.add_argument("--email")
    parser.add_argument("--employee-code", help="Employee ID to link (required for --role Employee).")
    args = parser.parse_args(argv)

    if get_settings().is_production:
        print("create_user is for development only. Use user management instead.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        employee_id = None
        if args.employee_code:
            employee = db.scalar(
                select(Employee).where(func.lower(Employee.employee_code) == args.employee_code.strip().lower())
            )
            if employee is None:
                print(f"Not created: no employee with ID {args.employee_code}.", file=sys.stderr)
                return 1
            employee_id = employee.id
        elif args.role == RoleName.EMPLOYEE:
            print("Not created: --employee-code is required for the Employee role.", file=sys.stderr)
            return 1

        email = args.email or ask_email()
        password = ask_password()
        try:
            user = create_user(db, email=email, password=password, role_name=args.role, employee_id=employee_id)
        except AppError as exc:
            print(f"Not created: {exc.message}", file=sys.stderr)
            return 1
    print(f"{args.role} account created: {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
