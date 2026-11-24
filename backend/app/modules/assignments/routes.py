"""Assignment history and overdue endpoints (Slice 5.3: ASN-07, ASN-08, EMP-04; owner's answers
N7, N8, N10-N13). Read-only: nothing here changes data, so nothing writes an audit row.

- GET /assignments/overdue : the overdue list (Admin and IT Manager; Employee 403)
- GET /me/assignments      : the logged-in Employee's own assets (Employee role only; staff 403, N13)

An employee's history for staff is GET /employees/{id}/assignments (employees/routes.py).
Assigning and returning live on the asset (assets/routes.py).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.assignments import service
from app.modules.assignments.schemas import AssignmentRead, MyAssignments, OverduePage
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import RoleName, User

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)
require_employee = require_roles(RoleName.EMPLOYEE)

router = APIRouter(prefix="/assignments", tags=["assignments"], responses=error_responses(401, 403))
me_router = APIRouter(prefix="/me", tags=["assignments"], responses=error_responses(401, 403))


@router.get("/overdue", response_model=OverduePage, summary="Overdue returns", dependencies=[Depends(require_staff)])
def list_overdue(
    params: PageParams = Depends(page_params),
    search: str | None = Query(
        None, max_length=100, description="Part of the asset ID, asset name, serial number, employee ID or name."
    ),
    db: Session = Depends(get_db),
) -> dict:
    """ASN-08, N7: assignments whose expected return date is before today (company timezone) and
    that are not returned. Most late first by default; sort by `expected_return_date`,
    `assignment_date`, `asset_code` or `employee` (prefix `-` for descending). No e-mail reminders (N7)."""
    page = service.list_overdue(db, params, search=search)
    page["items"] = [AssignmentRead.model_validate(service.read(a)) for a in page["items"]]
    return page


@me_router.get(
    "/assignments", response_model=MyAssignments, summary="My assets (current and past)",
    responses=error_responses(404),
)
def my_assignments(user: User = Depends(require_employee), db: Session = Depends(get_db)) -> dict:
    """N8: the logged-in Employee's own current assets and past assignments, read-only, found
    through the link between their login and their employee record. Leaves out condition notes and
    staff e-mails (N12). Admin and IT Manager: 403 (N13). Login not linked: **404** `employee_not_linked`."""
    employee = service.employee_of_login(db, user)
    held = service.employee_assignments(db, employee.id)
    return {
        "employee": employee,
        "current": [service.read(a, for_employee=True) for a in held["current"]],
        "past": [service.read(a, for_employee=True) for a in held["past"]],
    }
