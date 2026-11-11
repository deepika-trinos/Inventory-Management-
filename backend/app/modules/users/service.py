"""User and role database work, shared by the login code, the seed script and tests.

Slice 1.6 adds the Admin's user-management features here.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_password
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.employees.models import Employee
from app.modules.users.models import Role, User

# Simple shape check (something@something.something). Full checking of the
# address is not needed for login accounts created by an Admin.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    """Emails are stored and compared in lower case without spaces."""
    return email.strip().lower()


def validate_new_password(password: str) -> None:
    minimum = get_settings().password_min_length
    if len(password) < minimum:
        raise AppError(
            422, "weak_password", f"Password must be at least {minimum} characters long."
        )


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == normalize_email(email)))


def get_role_by_name(db: Session, name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        raise AppError(400, "unknown_role", f'Role "{name}" does not exist.')
    return role


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role_name: str,
    employee_id: int | None = None,
    is_active: bool = True,
) -> User:
    """Create a login account. The password is hashed; the plain text is never stored."""
    email = normalize_email(email)
    if not _EMAIL_RE.match(email) or len(email) > 255:
        raise AppError(422, "invalid_email", "Please enter a valid email address.")
    validate_new_password(password)
    if get_user_by_email(db, email) is not None:
        raise AppError(409, "email_taken", "A user with this email already exists.")
    role = get_role_by_name(db, role_name)
    if employee_id is not None:
        if db.get(Employee, employee_id) is None:
            raise AppError(404, "employee_not_found", "Employee record not found.")
        if db.scalar(select(User).where(User.employee_id == employee_id)) is not None:
            raise AppError(409, "employee_has_login", "This employee already has a login.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        employee_id=employee_id,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_role(
    db: Session,
    *,
    actor: User,
    user: User,
    new_role_name: str,
    context: AuditContext | None = None,
) -> User:
    """Give a user a different role, and record it in the audit log.

    The role change and its audit row are saved in ONE transaction: both or neither.
    Slice 1.6 exposes this through an Admin-only endpoint; any extra business
    rules (for example about the last Admin) must be confirmed before then.
    """
    new_role = get_role_by_name(db, new_role_name)
    if user.role_id == new_role.id:
        return user  # nothing changed, nothing to record

    before = audit.snapshot(user, ["role"])
    user.role = new_role
    try:
        audit.record(
            db,
            actor=actor,
            action=AuditAction.USER_ROLE_CHANGED,
            entity=user,
            before=before,
            after=audit.snapshot(user, ["role"]),
            context=context,
        )
        db.commit()
    except Exception:
        db.rollback()  # undo the role change AND the audit row
        raise
    return user
