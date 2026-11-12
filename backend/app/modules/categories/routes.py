"""Asset category endpoints: /api/v1/categories/... (Slice 2.1, AST-02).

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
from app.modules.categories import service
from app.modules.categories.models import AssetCategory
from app.modules.categories.schemas import (
    CategoryCreate,
    CategoryPage,
    CategoryRead,
    CategoryStatusField,
    CategoryUpdate,
    TrackingTypeField,
)
from app.modules.users.models import RoleName, User

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    dependencies=[Depends(require_staff)],  # every endpoint below: Admin or IT Manager
    responses=error_responses(401, 403),
)


@router.get("", response_model=CategoryPage, summary="List asset categories")
def list_categories(
    params: PageParams = Depends(page_params),
    search: str | None = Query(None, max_length=100, description="Part of a category name (any case)."),
    tracking_type: TrackingTypeField | None = Query(None, description="Only this tracking type."),
    status_filter: CategoryStatusField | None = Query(
        None, alias="status", description="Only active or only inactive."
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list, including inactive categories unless filtered. Sort by `name`,
    `tracking_type`, `status`, `created_at` or `updated_at` (prefix `-` for descending)."""
    return service.list_categories(
        db, params, search=search, tracking_type=tracking_type, status=status_filter
    )


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    responses=error_responses(409, 422),
)
def create_category(
    body: CategoryCreate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetCategory:
    """Create an active category.

    - Duplicate name (any upper/lower case): **409** `category_name_taken`
    - Blank name: **422** `invalid_name`
    - Writes audit action `category.created`.
    """
    return service.create_category(
        db,
        name=body.name,
        description=body.description,
        tracking_type=body.tracking_type,
        actor=user,
        context=context,
    )


@router.get(
    "/{category_id}", response_model=CategoryRead, summary="Get one category", responses=error_responses(404)
)
def get_category(category_id: int, db: Session = Depends(get_db)) -> AssetCategory:
    return service.get_category(db, category_id)


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Edit a category",
    responses=error_responses(404, 409, 422),
)
def update_category(
    category_id: int,
    body: CategoryUpdate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetCategory:
    """Send only the fields to change. `"description": null` clears it.
    Writes audit action `category.updated` when something changed.

    - Duplicate name: **409** `category_name_taken`
    - Changing `tracking_type` once items or assets use the category:
      **409** `tracking_type_locked` (applies from Slice 2.4 / 3.2 onward)
    """
    category = service.get_category(db, category_id)
    changes = body.model_dump(exclude_unset=True)  # only what was actually sent
    return service.update_category(db, actor=user, category=category, changes=changes, context=context)


@router.post(
    "/{category_id}/activate",
    response_model=CategoryRead,
    summary="Activate a category",
    responses=error_responses(404),
)
def activate_category(
    category_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetCategory:
    """Make the category selectable again. Writes audit action `category.activated`."""
    category = service.get_category(db, category_id)
    return service.set_active(db, actor=user, category=category, active=True, context=context)


@router.post(
    "/{category_id}/deactivate",
    response_model=CategoryRead,
    summary="Deactivate a category",
    responses=error_responses(404),
)
def deactivate_category(
    category_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetCategory:
    """Hide the category from new records (never deletes it, BR-12). It stays
    readable and existing records keep it. Writes audit action `category.deactivated`."""
    category = service.get_category(db, category_id)
    return service.set_active(db, actor=user, category=category, active=False, context=context)
