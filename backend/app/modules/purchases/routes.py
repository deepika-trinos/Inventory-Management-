"""Purchase endpoints: /api/v1/purchases/... (Slice 3.1, PUR-01 to PUR-04, PUR-08, BR-06).

ADMIN AND IT MANAGER ONLY (P6): the whole router requires one of those roles
(checked on the server for every request), so an Employee gets 403 on all of these.

There is deliberately NO delete endpoint (BR-12): a draft is cancelled instead.
Receiving (Slices 3.2 / 3.3) is the only thing that will change stock or create assets.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.audit.service import AuditContext, get_audit_context
from app.modules.auth.dependencies import require_roles
from app.modules.purchases import service
from app.modules.purchases.models import Purchase
from app.modules.purchases.schemas import (
    PurchaseCreate,
    PurchasePage,
    PurchaseRead,
    PurchaseStatusField,
    PurchaseUpdate,
)
from app.modules.users.models import RoleName, User

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)

router = APIRouter(
    prefix="/purchases",
    tags=["purchases"],
    dependencies=[Depends(require_staff)],  # every endpoint below: Admin or IT Manager
    responses=error_responses(401, 403),
)


@router.get("", response_model=PurchasePage, summary="List purchases")
def list_purchases(
    params: PageParams = Depends(page_params),
    search: str | None = Query(
        None, max_length=100, description="Part of the reference number, vendor name or purchase number."
    ),
    status_filter: PurchaseStatusField | None = Query(
        None, alias="status", description="Only draft, received or cancelled."
    ),
    vendor_id: int | None = Query(None, description="Only purchases from this vendor."),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list, newest first by default. Sort by `purchase_number`, `purchase_date`,
    `reference_number`, `vendor`, `status`, `created_at` or `updated_at` (prefix `-` for descending)."""
    return service.list_purchases(db, params, search=search, status=status_filter, vendor_id=vendor_id)


@router.post(
    "",
    response_model=PurchaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft purchase",
    responses=error_responses(404, 409, 422),
)
def create_purchase(
    body: PurchaseCreate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Purchase:
    """Create a **draft** purchase with at least one line. Changes no stock and creates no assets.

    - Vendor inactive: **409** `vendor_inactive`; stock item inactive: **409** `stock_item_inactive`;
      category inactive: **409** `category_inactive`; category tracked by quantity on a
      one-by-one line: **409** `category_not_serialized`
    - Same reference number for this vendor (any case, not cancelled): **409** `purchase_reference_taken`
    - No lines: **422** `lines_required`; bad line: **422** `invalid_line`;
      future date: **422** `purchase_date_in_future`
    - Writes audit action `purchase.created`.
    """
    return service.create_purchase(db, data=body.model_dump(), actor=user, context=context)


@router.get("/{purchase_id}", response_model=PurchaseRead, summary="Get one purchase", responses=error_responses(404))
def get_purchase(purchase_id: int, db: Session = Depends(get_db)) -> Purchase:
    return service.get_purchase(db, purchase_id)


@router.patch(
    "/{purchase_id}",
    response_model=PurchaseRead,
    summary="Edit a draft purchase",
    responses=error_responses(404, 409, 422),
)
def update_purchase(
    purchase_id: int,
    body: PurchaseUpdate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Purchase:
    """Send only the fields to change. `lines`, when sent, replaces all lines.
    Only a draft can be edited (**409** `purchase_not_draft`).
    Writes audit action `purchase.updated` when something changed."""
    purchase = service.get_purchase(db, purchase_id, lock=True)
    changes = body.model_dump(exclude_unset=True)  # only what was actually sent
    return service.update_purchase(db, actor=user, purchase=purchase, changes=changes, context=context)


@router.post(
    "/{purchase_id}/cancel",
    response_model=PurchaseRead,
    summary="Cancel a draft purchase",
    responses=error_responses(404, 409),
)
def cancel_purchase(
    purchase_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Purchase:
    """Cancel a draft. Final: it can never be edited or received afterwards.
    Nothing is deleted and no stock changes. Only a draft can be cancelled
    (**409** `purchase_not_draft`). Writes audit action `purchase.cancelled`."""
    purchase = service.get_purchase(db, purchase_id, lock=True)
    return service.cancel_purchase(db, actor=user, purchase=purchase, context=context)
