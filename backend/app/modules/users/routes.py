"""User management endpoints: /api/v1/users/... (AUTH-05). ADMIN ONLY.

The whole router requires the Admin role (checked on the server for every
request), so an IT Manager or Employee gets 403 on all of these.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.audit.service import AuditContext, get_audit_context
from app.modules.auth.dependencies import require_roles
from app.modules.users import service
from app.modules.users.models import RoleName, User
from app.modules.users.schemas import RoleChange, RoleNameField, UserCreate, UserPage, UserRead, UserUpdate

require_admin = require_roles(RoleName.ADMIN)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_admin)],  # every endpoint below: Admin only
    responses=error_responses(401, 403),
)


@router.get("", response_model=UserPage, summary="List users")
def list_users(
    params: PageParams = Depends(page_params),
    search: str | None = Query(None, max_length=100, description="Part of an email or employee name."),
    role: RoleNameField | None = Query(None, description="Only this role."),
    is_active: bool | None = Query(None, description="true = active only, false = inactive only."),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list. Sort by `email`, `role`, `is_active`, `last_login_at` or `created_at`
    (prefix `-` for descending)."""
    return service.list_users(db, params, search=search, role=role, is_active=is_active)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
    responses=error_responses(404, 409, 422),
)
def create_user(
    body: UserCreate,
    admin: User = Depends(require_admin),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> User:
    """Create a login with a temporary password and one role.

    - Duplicate email (any upper/lower case): **409** `email_taken`
    - Password too short: **422** `weak_password`
    - `employee_id` that doesn't exist: **404**; already linked to another user: **409**
    - Writes audit action `user.created`.
    """
    return service.create_user(
        db,
        email=body.email,
        password=body.password,
        role_name=body.role,
        employee_id=body.employee_id,
        actor=admin,
        context=context,
    )


@router.get("/{user_id}", response_model=UserRead, summary="Get one user", responses=error_responses(404))
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    return service.get_user(db, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update email or employee link",
    responses=error_responses(404, 409, 422),
)
def update_user(
    user_id: int,
    body: UserUpdate,
    admin: User = Depends(require_admin),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> User:
    """Send only the fields to change. `"employee_id": null` removes the link.
    Writes audit action `user.updated` when something changed."""
    user = service.get_user(db, user_id)
    changes = body.model_dump(exclude_unset=True)  # only what was actually sent
    return service.update_user(db, actor=admin, user=user, changes=changes, context=context)


@router.patch(
    "/{user_id}/role",
    response_model=UserRead,
    summary="Change a user's role",
    responses=error_responses(404, 409, 422),
)
def change_role(
    user_id: int,
    body: RoleChange,
    admin: User = Depends(require_admin),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> User:
    """Change the role. Writes audit action `user.role_changed`.

    - You cannot remove your own Admin role: **409** `cannot_change_self`
    - The last active Admin cannot be demoted: **409** `last_admin`
    - The change applies on the user's very next request.
    """
    user = service.get_user(db, user_id)
    return service.change_role(db, actor=admin, user=user, new_role_name=body.role, context=context)


@router.post(
    "/{user_id}/activate",
    response_model=UserRead,
    summary="Activate a user",
    responses=error_responses(404),
)
def activate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> User:
    """Allow the user to log in again. Writes audit action `user.activated`."""
    user = service.get_user(db, user_id)
    return service.set_active(db, actor=admin, user=user, active=True, context=context)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserRead,
    summary="Deactivate a user",
    responses=error_responses(404, 409),
)
def deactivate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> User:
    """Block the login (never deletes it). Their current token stops working on
    their next request. Writes audit action `user.deactivated`.

    - You cannot deactivate yourself: **409** `cannot_change_self`
    - The last active Admin cannot be deactivated: **409** `last_admin`
    """
    user = service.get_user(db, user_id)
    return service.set_active(db, actor=admin, user=user, active=False, context=context)
