"""Employee endpoints: /api/v1/employees/... (Slice 2.2, EMP-01 to EMP-03).

ADMIN AND IT MANAGER ONLY: the whole router requires one of those roles
(checked on the server for every request), so an Employee gets 403 on all of these.

There is deliberately NO delete endpoint (BR-12): deactivate instead.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.audit.service import AuditContext, get_audit_context
from app.modules.auth.dependencies import require_roles
from app.modules.employees import service
from app.modules.employees.models import Employee
from app.modules.employees.schemas import (
    EmployeeCreate,
    EmployeePage,
    EmployeeRead,
    EmployeeStatusField,
    EmployeeUpdate,
)
from app.modules.users.models import RoleName, User

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
    dependencies=[Depends(require_staff)],  # every endpoint below: Admin or IT Manager
    responses=error_responses(401, 403),
)


@router.get("", response_model=EmployeePage, summary="List employees")
def list_employees(
    params: PageParams = Depends(page_params),
    search: str | None = Query(None, max_length=100, description="Part of an employee ID, name or department."),
    status_filter: EmployeeStatusField | None = Query(None, alias="status", description="Only active or inactive."),
    department: str | None = Query(None, max_length=100, description="Exact department (any case)."),
    has_login: bool | None = Query(None, description="false = only employees without a linked login."),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list. Sort by `employee_code`, `full_name`, `department`, `designation`,
    `status`, `created_at` or `updated_at` (prefix `-` for descending)."""
    return service.list_employees(
        db, params, search=search, status=status_filter, department=department, has_login=has_login
    )


@router.get("/departments", response_model=list[str], summary="Departments in use")
def list_departments(db: Session = Depends(get_db)) -> list[str]:
    """Every department already typed for an employee, A-Z (for filters and suggestions)."""
    return service.list_departments(db)


@router.post(
    "",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee",
    responses=error_responses(409, 422),
)
def create_employee(
    body: EmployeeCreate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Employee:
    """Create an active employee.

    - Duplicate employee ID (any case): **409** `employee_code_taken`
    - Duplicate work email (any case): **409** `work_email_taken`
    - Bad email / phone: **422** `invalid_email` / `invalid_phone`
    - Writes audit action `employee.created`.
    """
    return service.create_employee(db, data=body.model_dump(), actor=user, context=context)


@router.get(
    "/{employee_id}", response_model=EmployeeRead, summary="Get one employee", responses=error_responses(404)
)
def get_employee(employee_id: int, db: Session = Depends(get_db)) -> Employee:
    return service.get_employee(db, employee_id)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Edit an employee",
    responses=error_responses(404, 409, 422),
)
def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Employee:
    """Send only the fields to change; `null` clears an optional field.
    Writes audit action `employee.updated` when something changed."""
    employee = service.get_employee(db, employee_id)
    changes = body.model_dump(exclude_unset=True)  # only what was actually sent
    return service.update_employee(db, actor=user, employee=employee, changes=changes, context=context)


@router.post(
    "/{employee_id}/activate",
    response_model=EmployeeRead,
    summary="Activate an employee",
    responses=error_responses(404),
)
def activate_employee(
    employee_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Employee:
    """Mark the employee active again. A linked login stays as it is (the Admin
    reactivates it on the Users page). Writes audit action `employee.activated`."""
    employee = service.get_employee(db, employee_id)
    return service.set_active(db, actor=user, employee=employee, active=True, context=context)


@router.post(
    "/{employee_id}/deactivate",
    response_model=EmployeeRead,
    summary="Deactivate an employee",
    responses=error_responses(404, 409),
)
def deactivate_employee(
    employee_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Employee:
    """Mark the employee inactive (never deletes, BR-12). A linked active login is
    deactivated in the same step (audit `user.deactivated` plus `employee.deactivated`).

    - The employee is linked to your own login: **409** `cannot_change_self`
    - The linked login is the last active Admin: **409** `last_admin`
    """
    employee = service.get_employee(db, employee_id)
    return service.set_active(db, actor=user, employee=employee, active=False, context=context)
