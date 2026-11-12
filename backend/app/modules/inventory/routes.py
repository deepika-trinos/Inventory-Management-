"""Stock item endpoints: /api/v1/stock-items/... (Slice 2.4, INV-01).

ADMIN AND IT MANAGER ONLY: the whole router requires one of those roles
(checked on the server for every request), so an Employee gets 403 on all of these.

There is deliberately NO delete endpoint (BR-12): deactivate instead.
quantity_on_hand is read-only here; stock movements change it (Slices 3.3, 4.4, 4.5).
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.audit.service import AuditContext, get_audit_context
from app.modules.auth.dependencies import require_roles
from app.modules.inventory import service
from app.modules.inventory.models import StockItem
from app.modules.inventory.schemas import (
    StockItemCreate,
    StockItemPage,
    StockItemRead,
    StockItemStatusField,
    StockItemUpdate,
)
from app.modules.users.models import RoleName, User

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)

router = APIRouter(
    prefix="/stock-items",
    tags=["stock items"],
    dependencies=[Depends(require_staff)],  # every endpoint below: Admin or IT Manager
    responses=error_responses(401, 403),
)


@router.get("", response_model=StockItemPage, summary="List stock items")
def list_stock_items(
    params: PageParams = Depends(page_params),
    search: str | None = Query(None, max_length=100, description="Part of the item name (any case)."),
    category_id: int | None = Query(None, description="Only items in this category."),
    status_filter: StockItemStatusField | None = Query(None, alias="status", description="Only active or inactive."),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list. Sort by `name`, `category`, `unit_of_measure`, `reorder_threshold`,
    `quantity_on_hand`, `status` or `updated_at` (prefix `-` for descending)."""
    return service.list_stock_items(db, params, search=search, category_id=category_id, status=status_filter)


@router.post(
    "",
    response_model=StockItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stock item",
    responses=error_responses(404, 409, 422),
)
def create_stock_item(
    body: StockItemCreate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> StockItem:
    """Create an active item tracked by quantity. Its quantity starts at 0.

    - Category tracked one by one: **409** `category_not_bulk`
    - Deactivated category: **409** `category_inactive`; unknown: **404** `category_not_found`
    - Same name already in that category (any case): **409** `stock_item_name_taken`
    - Negative threshold, unknown unit, or any `quantity_on_hand` sent: **422** `validation_error`
    - Writes audit action `stock_item.created`.
    """
    return service.create_stock_item(
        db,
        name=body.name,
        category_id=body.category_id,
        unit_of_measure=body.unit_of_measure,
        reorder_threshold=body.reorder_threshold,
        actor=user,
        context=context,
    )


@router.get(
    "/{item_id}", response_model=StockItemRead, summary="Get one stock item", responses=error_responses(404)
)
def get_stock_item(item_id: int, db: Session = Depends(get_db)) -> StockItem:
    return service.get_stock_item(db, item_id)


@router.patch(
    "/{item_id}",
    response_model=StockItemRead,
    summary="Edit a stock item",
    responses=error_responses(404, 409, 422),
)
def update_stock_item(
    item_id: int,
    body: StockItemUpdate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> StockItem:
    """Send only the fields to change: name, category_id, unit_of_measure,
    reorder_threshold. A new category must be an active bulk category.
    The unit locks once the item has stock (**409** `unit_locked`, from Slice 3.3).
    Writes audit action `stock_item.updated` when something changed."""
    item = service.get_stock_item(db, item_id)
    changes = body.model_dump(exclude_unset=True)
    return service.update_stock_item(db, actor=user, item=item, changes=changes, context=context)


@router.post(
    "/{item_id}/activate",
    response_model=StockItemRead,
    summary="Activate a stock item",
    responses=error_responses(404),
)
def activate_stock_item(
    item_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> StockItem:
    """Writes audit action `stock_item.activated`."""
    item = service.get_stock_item(db, item_id)
    return service.set_active(db, actor=user, item=item, active=True, context=context)


@router.post(
    "/{item_id}/deactivate",
    response_model=StockItemRead,
    summary="Deactivate a stock item",
    responses=error_responses(404, 409),
)
def deactivate_stock_item(
    item_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> StockItem:
    """Never deletes (BR-12). Only at zero stock: **409** `stock_not_zero` otherwise.
    Writes audit action `stock_item.deactivated`."""
    item = service.get_stock_item(db, item_id)
    return service.set_active(db, actor=user, item=item, active=False, context=context)
