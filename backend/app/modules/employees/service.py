"""Employees: list, get, create, edit, activate/deactivate (Slice 2.2, EMP-01 to EMP-03).

Used by the /employees endpoints (Admin and IT Manager) and the Users screen's
employee picker. Later: assignments (Phase 5, EMP-04/EMP-05).

Every change writes an audit row in the SAME transaction (BR-13, B11).

RULES
- employee_code is unique ignoring upper/lower case; work_email (optional) is
  stored in lower case (B5) and unique ignoring case.
- BR-12: employees are NEVER deleted, only deactivated. No delete function or
  endpoint exists.
- Deactivating an employee ALSO deactivates the linked login, in the same
  transaction, with its own user.deactivated audit row (decision B21). The R1
  rules apply to that login: you cannot deactivate your own login this way, and
  the last active Admin cannot be deactivated. Activating an employee does NOT
  reactivate the login: the Admin does that on the Users page.
"""

import re
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.employees.models import Employee, EmployeeStatus
from app.modules.users import service as users_service
from app.modules.users.models import User

# What the audit log records about an employee.
_AUDIT_FIELDS = ["employee_code", "full_name", "department", "designation", "work_email", "phone", "status"]

# Fields the employee list can be sorted by.
_SORTABLE = {
    "employee_code": func.lower(Employee.employee_code),
    "full_name": func.lower(Employee.full_name),
    "department": func.lower(Employee.department),
    "designation": func.lower(Employee.designation),
    "status": Employee.status,
    "created_at": Employee.created_at,
    "updated_at": Employee.updated_at,
}

# Phone: digits plus the usual separators (decision B22). Format is not checked further.
_PHONE_RE = re.compile(r"^\+?[0-9 ()./-]{3,30}$")

# Unique indexes (migration 0005) -> the error to show if two saves race each other.
_UNIQUE_INDEX_ERRORS = {
    "uq_employees_employee_code_lower": ("employee_code_taken", "An employee with this employee ID already exists."),
    "uq_employees_work_email_lower": ("work_email_taken", "Another employee already uses this work email."),
}


# ---- Small helpers ------------------------------------------------------------------
def _required_text(value: str, code: str, message: str) -> str:
    value = value.strip()
    if not value:
        raise AppError(422, code, message)
    return value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _clean_work_email(value: str | None) -> str | None:
    value = _optional_text(value)
    return users_service.validate_email(value) if value else None


def _clean_phone(value: str | None) -> str | None:
    value = _optional_text(value)
    if value and not _PHONE_RE.match(value):
        raise AppError(422, "invalid_phone", "Phone may contain digits, spaces, + ( ) . / and - only.")
    return value


def _clean(field: str, value: Any) -> Any:
    if field == "employee_code":
        return _required_text(value, "invalid_employee_code", "Please enter an employee ID.")
    if field == "full_name":
        return _required_text(value, "invalid_full_name", "Please enter the employee's name.")
    if field == "work_email":
        return _clean_work_email(value)
    if field == "phone":
        return _clean_phone(value)
    return _optional_text(value)  # department, designation


def get_employee(db: Session, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise AppError(404, "employee_not_found", "Employee not found.")
    return employee


def _ensure_unique(db: Session, *, code: str | None, email: str | None, except_id: int | None = None) -> None:
    if code is not None:
        clash = db.scalar(select(Employee).where(func.lower(Employee.employee_code) == code.lower()))
        if clash is not None and clash.id != except_id:
            raise AppError(409, "employee_code_taken", "An employee with this employee ID already exists.")
    if email is not None:
        clash = db.scalar(select(Employee).where(func.lower(Employee.work_email) == email.lower()))
        if clash is not None and clash.id != except_id:
            raise AppError(409, "work_email_taken", "Another employee already uses this work email.")


def _linked_user(db: Session, employee: Employee) -> User | None:
    return db.scalar(select(User).where(User.employee_id == employee.id))


def _commit(db: Session) -> None:
    """Commit; turn a unique-index race into the normal 409 error."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        for index, (code, message) in _UNIQUE_INDEX_ERRORS.items():
            if index in str(exc.orig):
                raise AppError(409, code, message) from None
        raise
    except Exception:
        db.rollback()
        raise


def _save(
    db: Session,
    *,
    actor: User | None,
    action: str,
    employee: Employee,
    before: dict[str, Any] | None,
    context: AuditContext | None,
) -> Employee:
    try:
        audit.record(
            db,
            actor=actor,
            action=action,
            entity=employee,
            before=before,
            after=audit.snapshot(employee, _AUDIT_FIELDS),
            context=context,
        )
    except Exception:
        db.rollback()
        raise
    _commit(db)
    db.refresh(employee)
    return employee


# ---- Reading ----------------------------------------------------------------------
def list_employees(
    db: Session,
    params: PageParams,
    *,
    search: str | None = None,
    status: str | None = None,
    department: str | None = None,
    has_login: bool | None = None,
) -> dict[str, Any]:
    """Paged list. `search` matches part of the employee ID, name or department
    (EMP-03, any case). `department` is an exact match ignoring case.
    `has_login=false` lists employees without a login (the Users screen's picker)."""
    stmt: Select = select(Employee)
    if search and search.strip():
        term = search.strip().lower()
        stmt = stmt.where(
            func.lower(Employee.employee_code).contains(term, autoescape=True)
            | func.lower(Employee.full_name).contains(term, autoescape=True)
            | func.lower(Employee.department).contains(term, autoescape=True)
        )
    if status:
        stmt = stmt.where(Employee.status == status)
    if department and department.strip():
        stmt = stmt.where(func.lower(Employee.department) == department.strip().lower())
    if has_login is not None:
        linked = select(User.id).where(User.employee_id == Employee.id).exists()
        stmt = stmt.where(linked if has_login else ~linked)
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="full_name")


def list_departments(db: Session) -> list[str]:
    """Departments already in use (for the filter and the form's suggestions),
    one spelling per department ignoring case, sorted A-Z."""
    rows = db.execute(
        select(func.min(Employee.department))
        .where(Employee.department.is_not(None))
        .group_by(func.lower(Employee.department))
        .order_by(func.lower(Employee.department))
    ).scalars()
    return list(rows)


# ---- Changing ---------------------------------------------------------------------
def create_employee(
    db: Session,
    *,
    data: dict[str, Any],
    actor: User | None = None,
    context: AuditContext | None = None,
) -> Employee:
    """Create an active employee (audit: employee.created)."""
    fields = ("employee_code", "full_name", "department", "designation", "work_email", "phone")
    values = {field: _clean(field, data.get(field)) if field in data else None for field in fields}
    if values["employee_code"] is None or values["full_name"] is None:
        raise AppError(422, "validation_error", "Employee ID and name are required.")
    _ensure_unique(db, code=values["employee_code"], email=values["work_email"])
    employee = Employee(**values, status=EmployeeStatus.ACTIVE)
    db.add(employee)
    return _save(db, actor=actor, action=AuditAction.EMPLOYEE_CREATED, employee=employee, before=None, context=context)


def update_employee(
    db: Session,
    *,
    actor: User | None,
    employee: Employee,
    changes: dict[str, Any],
    context: AuditContext | None = None,
) -> Employee:
    """Change any detail except status (audit: employee.updated).

    `changes` holds only the fields actually sent; null clears an optional
    field (employee ID and name cannot be cleared). Works on inactive employees too.
    """
    before = audit.snapshot(employee, _AUDIT_FIELDS)
    new_values: dict[str, Any] = {}
    for field, value in changes.items():
        if field in ("employee_code", "full_name") and value is None:
            continue  # required fields: "null" means "leave as it is"
        cleaned = _clean(field, value)
        if cleaned != getattr(employee, field):
            new_values[field] = cleaned

    if not new_values:
        return employee  # nothing to save or record
    code = new_values.get("employee_code")
    _ensure_unique(
        db,
        code=code if code is not None and code.lower() != employee.employee_code.lower() else None,
        email=new_values.get("work_email"),
        except_id=employee.id,
    )
    for field, value in new_values.items():
        setattr(employee, field, value)
    return _save(db, actor=actor, action=AuditAction.EMPLOYEE_UPDATED, employee=employee, before=before, context=context)


def set_active(
    db: Session,
    *,
    actor: User | None,
    employee: Employee,
    active: bool,
    context: AuditContext | None = None,
) -> Employee:
    """Activate or deactivate (audit: employee.activated / employee.deactivated).

    Never deletes anything (BR-12). Deactivating also deactivates the linked
    login in the same transaction (B21); activating leaves the login as it is.
    """
    new_status = EmployeeStatus.ACTIVE if active else EmployeeStatus.INACTIVE
    if employee.status == new_status:
        return employee  # already in that state

    login = None if active else _linked_user(db, employee)
    if login is not None and login.is_active:
        if actor is not None and actor.id == login.id:
            raise AppError(
                409,
                "cannot_change_self",
                "This employee record is linked to your own login. Ask another Admin to deactivate it.",
            )
        users_service.ensure_can_deactivate(db, actor, login)
    else:
        login = None

    before = audit.snapshot(employee, _AUDIT_FIELDS)
    employee.status = new_status
    try:
        if login is not None:
            login_before = audit.snapshot(login, users_service.AUDIT_FIELDS)
            login.is_active = False
            audit.record(
                db,
                actor=actor,
                action=AuditAction.USER_DEACTIVATED,
                entity=login,
                before=login_before,
                after={**audit.snapshot(login, users_service.AUDIT_FIELDS), "reason": "employee_deactivated"},
                context=context,
            )
    except Exception:
        db.rollback()
        raise
    action = AuditAction.EMPLOYEE_ACTIVATED if active else AuditAction.EMPLOYEE_DEACTIVATED
    saved = _save(db, actor=actor, action=action, employee=employee, before=before, context=context)
    if login is not None:
        db.refresh(login)
    return saved
