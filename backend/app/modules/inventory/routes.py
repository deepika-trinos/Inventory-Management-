"""Stock item endpoints: /api/v1/stock-items/... (Slice 2.4, INV-01; Slice 4.3: the
low-stock flag and filter, and each item's movement history, INV-02, INV-05, INV-06).

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
    StockAdjust,
    StockChangeResult,
    StockIssue,
    StockItemCreate,
    StockItemPage,
    StockMovementPage,
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
    low_stock: bool | None = Query(
        None, description="true = only active items at or below their reorder threshold; false = all others."
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list. Each item says whether it is `low_stock` (active, quantity on hand at
    or below the reorder threshold). Filters combine. Sort by `name`, `category`,
    `unit_of_measure`, `reorder_threshold`, `quantity_on_hand`, `status` or `updated_at`
    (prefix `-` for descending)."""
    return service.list_stock_items(
        db, params, search=search, category_id=category_id, status=status_filter, low_stock=low_stock
    )


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


@router.get(
    "/{item_id}/movements", response_model=StockMovementPage, summary="A stock item's movement history",
    responses=error_responses(404),
)
def list_movements(item_id: int, params: PageParams = Depends(page_params), db: Session = Depends(get_db)) -> dict:
    """Every stock movement of this item (INV-05), newest first in the order saved, with
    type, signed change, balance after, business date, saved at, who, reason and what
    caused it (a receipt's purchase). Inactive items keep their history.
    Unknown item: **404** `stock_item_not_found`."""
    item = service.get_stock_item(db, item_id)
    return service.list_movements(db, item, params)


def _change_result(item: StockItem, movement) -> dict:
    return {"item": item, "movement": service.movement_read(movement)}


@router.post(
    "/{item_id}/issue", response_model=StockChangeResult, summary="Issue stock",
    responses=error_responses(404, 409, 422),
)
def issue_stock(
    item_id: int,
    body: StockIssue,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> dict:
    """Hand out stock (INV-04; owner's answer A4). Reason required (up to 500); employee
    optional (active only); date today by default, earlier allowed, future refused.
    Balance and movement are saved together with audit `stock.issued` (one transaction).

    - More than on hand: **409** `insufficient_stock` (exactly 0 is allowed)
    - Inactive item: **409** `stock_item_inactive`; unknown item: **404** `stock_item_not_found`
    - Unknown employee: **404** `employee_not_found`; inactive employee: **409** `employee_inactive`
    - Missing / too long reason: **422** `invalid_reason`; future date: **422** `movement_date_in_future`"""
    item, movement = service.issue_stock(
        db, actor=user, item_id=item_id, quantity=body.quantity, reason=body.reason,
        employee_id=body.employee_id, movement_date=body.movement_date, context=context,
    )
    return _change_result(item, movement)


@router.post(
    "/{item_id}/adjust", response_model=StockChangeResult, summary="Adjust stock",
    responses=error_responses(404, 409, 422),
)
def adjust_stock(
    item_id: int,
    body: StockAdjust,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> dict:
    """Correct the balance (owner's answer A5): `direction` add or remove, `quantity`, a
    required reason. No approval step (Q7). Saved with audit `stock.adjusted`.

    - Removing more than on hand: **409** `insufficient_stock`
    - Inactive item: **409** `stock_item_inactive`; unknown item: **404** `stock_item_not_found`
    - Missing / too long reason: **422** `invalid_reason`; future date: **422** `movement_date_in_future`"""
    item, movement = service.adjust_stock(
        db, actor=user, item_id=item_id, direction=body.direction, quantity=body.quantity,
        reason=body.reason, movement_date=body.movement_date, context=context,
    )
    return _change_result(item, movement)


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
    The unit locks once the item has any stock movement (**409** `unit_locked`, B36).
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
