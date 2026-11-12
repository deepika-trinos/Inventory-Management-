"""Stock items: list, get, create, edit, activate/deactivate (Slice 2.4, INV-01).

Used by the /stock-items endpoints (Admin and IT Manager). Later: purchases
(3.1, 3.3), stock issue/adjust (4.4) and opening stock (4.5) call
ensure_stock_item_usable() and change quantity_on_hand through movements.

Every change writes an audit row in the SAME transaction (BR-13, B11).

RULES
- PRD 9.2: a stock item's category must be tracked BY QUANTITY ('bulk') and be
  ACTIVE when chosen (on create, or when the category is changed):
  errors category_not_bulk / category_inactive.
- Name is unique within its category, ignoring upper/lower case.
- quantity_on_hand is never set here: it starts at 0 and only stock movements
  change it (Slices 3.3, 4.4, 4.5).
- The unit of measure locks once the item has stock history (B36); the guard
  starts to apply from Slice 3.3 (see _has_stock_history).
- BR-12: never deleted. Deactivation only at zero stock (B38).
"""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.core.text import required_text
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.categories import service as categories_service
from app.modules.categories.models import AssetCategory, TrackingType
from app.modules.inventory.models import StockItem, StockItemStatus
from app.modules.users.models import User

# What the audit log records about a stock item (category by id and name).
_AUDIT_FIELDS = ["name", "category_id", "unit_of_measure", "reorder_threshold", "quantity_on_hand", "status"]

# Fields the list can be sorted by.
_SORTABLE = {
    "name": func.lower(StockItem.name),
    "category": func.lower(AssetCategory.name),
    "unit_of_measure": StockItem.unit_of_measure,
    "reorder_threshold": StockItem.reorder_threshold,
    "quantity_on_hand": StockItem.quantity_on_hand,
    "status": StockItem.status,
    "updated_at": StockItem.updated_at,
}

_NAME_INDEX = "uq_stock_items_category_name_lower"
_EDITABLE = ("name", "category_id", "unit_of_measure", "reorder_threshold")


# ---- Small helpers ------------------------------------------------------------------
def _name_taken_error() -> AppError:
    return AppError(409, "stock_item_name_taken", "This category already has a stock item with this name.")


def _snapshot(item: StockItem, db: Session) -> dict[str, Any]:
    data = audit.snapshot(item, _AUDIT_FIELDS)
    category = db.get(AssetCategory, item.category_id)
    data["category"] = category.name if category else None
    return data


def get_stock_item(db: Session, item_id: int) -> StockItem:
    item = db.get(StockItem, item_id)
    if item is None:
        raise AppError(404, "stock_item_not_found", "Stock item not found.")
    return item


def _ensure_bulk_category(db: Session, category_id: int) -> AssetCategory:
    """The category to file a stock item under: must exist, be active (B13) and be 'bulk' (PRD 9.2)."""
    category = db.get(AssetCategory, category_id)
    if category is None:
        raise AppError(404, "category_not_found", "Category not found.")
    if category.tracking_type != TrackingType.BULK:
        raise AppError(
            409,
            "category_not_bulk",
            f'Category "{category.name}" is tracked one by one (serialized). '
            "Stock items need a category tracked by quantity.",
        )
    return categories_service.ensure_category_selectable(db, category_id)  # category_inactive


def _ensure_name_free(db: Session, category_id: int, name: str, *, except_id: int | None = None) -> None:
    clash = db.scalar(
        select(StockItem).where(
            StockItem.category_id == category_id, func.lower(StockItem.name) == name.lower()
        )
    )
    if clash is not None and clash.id != except_id:
        raise _name_taken_error()


def _has_stock_history(db: Session, item: StockItem) -> bool:
    """Has this item ever had stock? Locks the unit of measure (B36).

    NOTE: there are no stock movements yet, so quantity_on_hand is always 0 and
    this returns False: the unit lock does not apply yet. It STARTS TO APPLY in
    Slice 3.3, which adds the stock_movements table: add "or any movement exists
    for this item" here.
    """
    _ = db
    return item.quantity_on_hand > 0


def ensure_stock_item_usable(db: Session, item_id: int) -> StockItem:
    """Return the item if NEW stock activity may use it (purchase lines 3.1,
    issue 4.4, opening stock 4.5); otherwise raise. Not called anywhere yet."""
    item = get_stock_item(db, item_id)
    if not item.is_active:
        raise AppError(409, "stock_item_inactive", f'Stock item "{item.name}" is deactivated.')
    return item


def _save(
    db: Session,
    *,
    actor: User | None,
    action: str,
    item: StockItem,
    before: dict[str, Any] | None,
    context: AuditContext | None,
) -> StockItem:
    """Write the audit row and commit the change together; undo both on any error."""
    try:
        db.flush()
        audit.record(
            db, actor=actor, action=action, entity=item, before=before, after=_snapshot(item, db), context=context
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _NAME_INDEX in str(exc.orig):
            raise _name_taken_error() from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(item)
    return item


# ---- Reading ----------------------------------------------------------------------
def list_stock_items(
    db: Session,
    params: PageParams,
    *,
    search: str | None = None,
    category_id: int | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Paged list. `search` matches part of the name, ignoring case."""
    stmt: Select = select(StockItem).join(AssetCategory, StockItem.category_id == AssetCategory.id)
    if search and search.strip():
        stmt = stmt.where(func.lower(StockItem.name).contains(search.strip().lower(), autoescape=True))
    if category_id is not None:
        stmt = stmt.where(StockItem.category_id == category_id)
    if status:
        stmt = stmt.where(StockItem.status == status)
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="name")


# ---- Changing ---------------------------------------------------------------------
def create_stock_item(
    db: Session,
    *,
    name: str,
    category_id: int,
    unit_of_measure: str,
    reorder_threshold: int,
    actor: User | None = None,
    context: AuditContext | None = None,
) -> StockItem:
    """Create an active stock item with quantity 0 (audit: stock_item.created)."""
    name = required_text(name, "invalid_name", "Please enter the item's name.")
    _ensure_bulk_category(db, category_id)
    _ensure_name_free(db, category_id, name)
    item = StockItem(
        name=name,
        category_id=category_id,
        unit_of_measure=unit_of_measure,
        reorder_threshold=reorder_threshold,
        quantity_on_hand=0,
        status=StockItemStatus.ACTIVE,
    )
    db.add(item)
    return _save(db, actor=actor, action=AuditAction.STOCK_ITEM_CREATED, item=item, before=None, context=context)


def update_stock_item(
    db: Session,
    *,
    actor: User | None,
    item: StockItem,
    changes: dict[str, Any],
    context: AuditContext | None = None,
) -> StockItem:
    """Change name, category, unit and/or threshold (audit: stock_item.updated).

    `changes` holds only the fields actually sent (null = leave as it is).
    A NEW category must be an active bulk category. Works on inactive items too.
    """
    before = _snapshot(item, db)
    new: dict[str, Any] = {}
    for field in _EDITABLE:
        value = changes.get(field)
        if value is None:
            continue
        if field == "name":
            value = required_text(value, "invalid_name", "Please enter the item's name.")
        if value != getattr(item, field):
            new[field] = value

    if not new:
        return item  # nothing to save or record
    if "category_id" in new:
        _ensure_bulk_category(db, new["category_id"])
    if "unit_of_measure" in new and _has_stock_history(db, item):
        raise AppError(
            409,
            "unit_locked",
            "The unit of measure cannot be changed because this item already has stock.",
        )
    name = new.get("name", item.name)
    category_id = new.get("category_id", item.category_id)
    if "category_id" in new or name.lower() != item.name.lower():
        _ensure_name_free(db, category_id, name, except_id=item.id)
    for field, value in new.items():
        setattr(item, field, value)
    if "category_id" in new:
        item.category = db.get(AssetCategory, new["category_id"])
    return _save(db, actor=actor, action=AuditAction.STOCK_ITEM_UPDATED, item=item, before=before, context=context)


def set_active(
    db: Session,
    *,
    actor: User | None,
    item: StockItem,
    active: bool,
    context: AuditContext | None = None,
) -> StockItem:
    """Activate or deactivate (audit: stock_item.activated / stock_item.deactivated).

    Never deletes (BR-12). Deactivation only at zero stock (B38): with no stock
    movements yet (until Slice 3.3) the quantity is always 0, so it never triggers.
    Activating does not check the category: the item keeps the category it has.
    """
    new_status = StockItemStatus.ACTIVE if active else StockItemStatus.INACTIVE
    if item.status == new_status:
        return item  # already in that state
    if not active and item.quantity_on_hand > 0:
        raise AppError(
            409,
            "stock_not_zero",
            f"{item.quantity_on_hand} {item.unit_of_measure} are still in stock. "
            "Issue or adjust the stock to 0 before deactivating.",
        )
    before = _snapshot(item, db)
    item.status = new_status
    action = AuditAction.STOCK_ITEM_ACTIVATED if active else AuditAction.STOCK_ITEM_DEACTIVATED
    return _save(db, actor=actor, action=action, item=item, before=before, context=context)
