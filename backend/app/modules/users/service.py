"""User accounts: create, list, update, change role, activate/deactivate.

Used by the Admin-only /users endpoints (Slice 1.6), the login code, the seed
scripts and tests.

Every change writes an audit row in the SAME transaction (Slice 1.4 helper),
so a change is never saved without its audit row, or the other way round.
Audit data shows email, role, status and employee link: never passwords.

SAFETY RULES (decisions.md, R1, decided in Slice 1.6):
- An Admin cannot deactivate themselves or remove their own Admin role.
- The last active Admin cannot be deactivated or demoted.
- Email addresses are unique, ignoring upper/lower case.
"""

import re
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.core.security import hash_password
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.employees.models import Employee
from app.modules.users.models import Role, RoleName, User

# Simple shape check (something@something.something). Full checking of the
# address is not needed for login accounts created by an Admin.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# What the audit log records about a user (never the password hash).
_AUDIT_FIELDS = ["email", "role", "is_active", "employee_id"]

# Fields the user list can be sorted by.
_SORTABLE = {
    "email": User.email,
    "role": Role.name,
    "is_active": User.is_active,
    "last_login_at": User.last_login_at,
    "created_at": User.created_at,
}


# ---- Small helpers ------------------------------------------------------------------
def normalize_email(email: str) -> str:
    """Emails are stored and compared in lower case without spaces."""
    return email.strip().lower()


def _validate_email(email: str) -> str:
    email = normalize_email(email)
    if not _EMAIL_RE.match(email) or len(email) > 255:
        raise AppError(422, "invalid_email", "Please enter a valid email address.")
    return email


def validate_new_password(password: str) -> None:
    minimum = get_settings().password_min_length
    if len(password) < minimum:
        raise AppError(
            422, "weak_password", f"Password must be at least {minimum} characters long."
        )


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == normalize_email(email)))


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "user_not_found", "User not found.")
    return user


def get_role_by_name(db: Session, name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        raise AppError(400, "unknown_role", f'Role "{name}" does not exist.')
    return role


def _ensure_email_free(db: Session, email: str, *, except_user_id: int | None = None) -> None:
    existing = get_user_by_email(db, email)
    if existing is not None and existing.id != except_user_id:
        raise AppError(409, "email_taken", "A user with this email already exists.")


def _ensure_employee_linkable(db: Session, employee_id: int, *, except_user_id: int | None = None) -> None:
    if db.get(Employee, employee_id) is None:
        raise AppError(404, "employee_not_found", "Employee record not found.")
    linked = db.scalar(select(User).where(User.employee_id == employee_id))
    if linked is not None and linked.id != except_user_id:
        raise AppError(409, "employee_has_login", "This employee is already linked to another user.")


def _other_active_admin_count(db: Session, user: User) -> int:
    """How many OTHER active Admins exist. Their rows are locked until this
    transaction ends, so two Admins cannot remove each other at the same moment."""
    ids = db.scalars(
        select(User.id)
        .join(Role)
        .where(Role.name == RoleName.ADMIN, User.is_active.is_(True), User.id != user.id)
        .with_for_update(of=User)
    ).all()
    return len(ids)


def _ensure_not_losing_last_admin(db: Session, actor: User | None, user: User, what: str) -> None:
    """Called before an Admin loses Admin access (demotion or deactivation)."""
    if user.role.name != RoleName.ADMIN or not user.is_active:
        return
    if actor is not None and actor.id == user.id:
        raise AppError(
            409,
            "cannot_change_self",
            f"You cannot {what} your own account. Ask another Admin to do it.",
        )
    if _other_active_admin_count(db, user) == 0:
        raise AppError(
            409,
            "last_admin",
            f"You cannot {what} the last active Admin. Make another user an Admin first.",
        )


def _save(
    db: Session,
    *,
    actor: User | None,
    action: str,
    user: User,
    before: dict[str, Any] | None,
    context: AuditContext | None,
) -> User:
    """Write the audit row and commit the change together; undo both on any error."""
    try:
        audit.record(
            db,
            actor=actor,
            action=action,
            entity=user,
            before=before,
            after=audit.snapshot(user, _AUDIT_FIELDS),
            context=context,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user


# ---- Reading ----------------------------------------------------------------------
def list_users(
    db: Session,
    params: PageParams,
    *,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """Paged user list. `search` matches email or the linked employee's name."""
    stmt: Select = select(User).join(Role).outerjoin(Employee, User.employee_id == Employee.id)
    if search:
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(func.lower(User.email).like(pattern), func.lower(Employee.full_name).like(pattern))
        )
    if role:
        stmt = stmt.where(Role.name == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="email")


# ---- Changing ---------------------------------------------------------------------
def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role_name: str,
    employee_id: int | None = None,
    is_active: bool = True,
    actor: User | None = None,
    context: AuditContext | None = None,
) -> User:
    """Create a login account (audit: user.created).

    The password is hashed; the plain text is never stored or logged.
    `actor` is the Admin doing it, or None for the seed scripts (a system action).
    """
    email = _validate_email(email)
    validate_new_password(password)
    _ensure_email_free(db, email)
    role = get_role_by_name(db, role_name)
    if employee_id is not None:
        _ensure_employee_linkable(db, employee_id)

    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        employee_id=employee_id,
        is_active=is_active,
    )
    db.add(user)
    return _save(db, actor=actor, action=AuditAction.USER_CREATED, user=user, before=None, context=context)


def update_user(
    db: Session,
    *,
    actor: User,
    user: User,
    changes: dict[str, Any],
    context: AuditContext | None = None,
) -> User:
    """Change email and/or employee link (audit: user.updated).

    `changes` holds only the fields the Admin actually sent. employee_id=None
    removes the link. Role and active status have their own actions below.
    """
    before = audit.snapshot(user, _AUDIT_FIELDS)
    changed = False

    if "email" in changes and changes["email"] is not None:
        email = _validate_email(changes["email"])
        if email != user.email:
            _ensure_email_free(db, email, except_user_id=user.id)
            user.email = email
            changed = True

    if "employee_id" in changes and changes["employee_id"] != user.employee_id:
        if changes["employee_id"] is not None:
            _ensure_employee_linkable(db, changes["employee_id"], except_user_id=user.id)
        user.employee_id = changes["employee_id"]
        changed = True

    if not changed:
        return user  # nothing to save or record
    return _save(db, actor=actor, action=AuditAction.USER_UPDATED, user=user, before=before, context=context)


def change_role(
    db: Session,
    *,
    actor: User | None,
    user: User,
    new_role_name: str,
    context: AuditContext | None = None,
) -> User:
    """Give a user a different role (audit: user.role_changed)."""
    new_role = get_role_by_name(db, new_role_name)
    if user.role_id == new_role.id:
        return user  # nothing changed, nothing to record
    if new_role.name != RoleName.ADMIN:
        _ensure_not_losing_last_admin(db, actor, user, "remove the Admin role from")

    before = audit.snapshot(user, _AUDIT_FIELDS)
    user.role = new_role
    return _save(db, actor=actor, action=AuditAction.USER_ROLE_CHANGED, user=user, before=before, context=context)


def set_active(
    db: Session,
    *,
    actor: User | None,
    user: User,
    active: bool,
    context: AuditContext | None = None,
) -> User:
    """Activate or deactivate a login (audit: user.activated / user.deactivated).

    Never deletes anything (BR-12). A deactivated user cannot log in, and their
    existing token stops working on their next request.
    """
    if user.is_active == active:
        return user  # already in that state
    if not active:
        _ensure_not_losing_last_admin(db, actor, user, "deactivate")

    before = audit.snapshot(user, _AUDIT_FIELDS)
    user.is_active = active
    action = AuditAction.USER_ACTIVATED if active else AuditAction.USER_DEACTIVATED
    return _save(db, actor=actor, action=action, user=user, before=before, context=context)
