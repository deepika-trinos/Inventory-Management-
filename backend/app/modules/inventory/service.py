"""Stock items: list, get, create, edit, activate/deactivate (Slice 2.4, INV-01),
and stock movements (Slice 3.3, INV-03, INV-05, INV-07, BR-09, BR-10).

Used by the /stock-items endpoints (Admin and IT Manager). Purchases (3.1, 3.3),
stock issue/adjust (4.4) and opening stock (4.5) call ensure_stock_item_usable(),
lock_stock_items() and record_movement(): the ONLY way quantity_on_hand changes.

Every change writes an audit row in the SAME transaction (BR-13, B11).

RULES
- PRD 9.2: a stock item's category must be tracked BY QUANTITY ('bulk') and be
  ACTIVE when chosen (on create, or when the category is changed):
  errors category_not_bulk / category_inactive.
- Name is unique within its category, ignoring upper/lower case.
- quantity_on_hand is never set by create / edit: it starts at 0 and only
  record_movement() changes it, together with a movement row (B39).
- Stock never goes below 0 (INV-07, BR-10): `insufficient_stock` (C7).
- The unit of measure locks once the item has stock history: any movement, or
  stock on hand (B36).
- BR-12: never deleted. Deactivation only at zero stock (B38).
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Select, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.core.text import optional_text, required_text
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.categories import service as categories_service
from app.modules.categories.models import AssetCategory, TrackingType
from app.modules.inventory.models import (
    REASON_MAX_LENGTH,
    MovementType,
    StockItem,
    StockItemStatus,
    StockMovement,
)
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
    """Has this item ever had stock? Locks the unit of measure (B36): any stock
    movement (even if the balance is back to 0), or stock on hand."""
    if item.quantity_on_hand > 0:
        return True
    return bool(db.scalar(select(exists().where(StockMovement.stock_item_id == item.id))))


def ensure_stock_item_usable(db: Session, item_id: int) -> StockItem:
    """Return the item if NEW stock activity may use it (purchase lines 3.1,
    issue 4.4, opening stock 4.5); otherwise raise. Called by purchase lines
    since Slice 3.1 (only for items newly added to a draft, B45)."""
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
    low_stock: bool | None = None,
) -> dict[str, Any]:
    """Paged list. `search` matches part of the name, ignoring case. `low_stock=True`
    keeps only active items at or below their reorder threshold (INV-06, B37, G1);
    `False` keeps every other item. All filters combine.

    Rows with the same sort value (e.g. two items in one category) are ordered by id in
    the sort's direction, so the order is stable and paging never repeats or skips a row (E10)."""
    stmt: Select = select(StockItem).join(AssetCategory, StockItem.category_id == AssetCategory.id)
    if search and search.strip():
        stmt = stmt.where(func.lower(StockItem.name).contains(search.strip().lower(), autoescape=True))
    if category_id is not None:
        stmt = stmt.where(StockItem.category_id == category_id)
    if status:
        stmt = stmt.where(StockItem.status == status)
    if low_stock is True:
        stmt = stmt.where(StockItem.low_stock_condition())
    elif low_stock is False:
        stmt = stmt.where(~StockItem.low_stock_condition())
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="name", tiebreaker=StockItem.id)


def list_movements(db: Session, item: StockItem, params: PageParams) -> dict[str, Any]:
    """The item's movement history (INV-05, Slice 4.3): newest first in the order the
    movements were SAVED (G2), so `balance_after` reads as a running balance. Movements
    saved together (e.g. two lines of one receipt, C6) keep their order by id.
    Each row says who saved it, when, the business date, and what caused it."""
    from app.modules.purchases.models import Purchase, PurchaseLine

    stmt = select(StockMovement).where(StockMovement.stock_item_id == item.id)
    page = paginate(
        db, stmt, params, sortable={"created_at": StockMovement.created_at},
        default_sort="-created_at", tiebreaker=StockMovement.id,
    )
    line_ids = {m.purchase_line_id for m in page["items"] if m.purchase_line_id is not None}
    references: dict[int, dict[str, Any]] = {}
    if line_ids:
        rows = db.execute(
            select(PurchaseLine.id, Purchase.id, Purchase.purchase_number)
            .join(Purchase, PurchaseLine.purchase_id == Purchase.id)
            .where(PurchaseLine.id.in_(line_ids))
        )
        references = {
            line_id: {"purchase_id": pid, "purchase_number": number, "purchase_line_id": line_id}
            for line_id, pid, number in rows
        }
    page["items"] = [
        {
            "id": m.id,
            "movement_type": m.movement_type,
            "direction": "in" if m.movement_type in MovementType.INCOMING else "out",
            "quantity": m.quantity,
            "change": m.quantity if m.movement_type in MovementType.INCOMING else -m.quantity,
            "balance_after": m.balance_after,
            "movement_date": m.movement_date,
            "created_at": m.created_at,
            "created_by": m.created_by,
            "reason": m.reason,
            "reference": references.get(m.purchase_line_id) if m.purchase_line_id is not None else None,
            "issued_to": m.issued_to,
        }
        for m in page["items"]
    ]
    return page


def movement_read(m: StockMovement) -> dict[str, Any]:
    """One movement in the same shape as the history rows (no purchase reference: only
    receipts have one, and issues / adjustments never do)."""
    incoming = m.movement_type in MovementType.INCOMING
    return {
        "id": m.id, "movement_type": m.movement_type, "direction": "in" if incoming else "out",
        "quantity": m.quantity, "change": m.quantity if incoming else -m.quantity,
        "balance_after": m.balance_after, "movement_date": m.movement_date, "created_at": m.created_at,
        "created_by": m.created_by, "reason": m.reason, "reference": None, "issued_to": m.issued_to,
    }


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

    Never deletes (BR-12). Deactivation only at zero stock (B38): received stock
    must be issued or adjusted to 0 first (Slice 4.4).
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


# ---- Stock movements (Slice 3.3) --------------------------------------------------
def lock_stock_items(db: Session, item_ids: set[int] | list[int]) -> dict[int, StockItem]:
    """Lock these stock items' rows until commit (SELECT ... FOR UPDATE) and reload
    their CURRENT balances. Rows are locked in id order, so two receipts touching
    the same items wait for each other instead of deadlocking. Call this before
    record_movement() so two people changing the same item's stock at the same
    moment cannot lose an update."""
    ids = sorted(set(item_ids))
    if not ids:
        return {}
    found = list(db.scalars(select(StockItem.id).where(StockItem.id.in_(ids)).order_by(StockItem.id).with_for_update()))
    if len(found) != len(ids):
        raise AppError(404, "stock_item_not_found", "Stock item not found.")
    items = db.scalars(
        select(StockItem).where(StockItem.id.in_(ids)).execution_options(populate_existing=True)
    ).unique().all()
    return {item.id: item for item in items}


def insufficient_stock_error(item: StockItem, wanted: int) -> AppError:
    return AppError(
        409,
        "insufficient_stock",
        f'Only {item.quantity_on_hand} {item.unit_of_measure} of "{item.name}" in stock '
        f"({wanted} requested). Stock cannot go below 0.",
        {"stock_item_id": item.id, "quantity_on_hand": item.quantity_on_hand, "requested": wanted},
    )


def record_movement(
    db: Session,
    *,
    item: StockItem,
    movement_type: str,
    quantity: int,
    movement_date: date,
    actor: User,
    purchase_line_id: int | None = None,
    reason: str | None = None,
    issued_to_employee_id: int | None = None,
) -> StockMovement:
    """Add ONE stock movement and change the item's balance by it, in the caller's
    transaction (B39). Does NOT commit: the caller commits (with its audit row)
    or rolls back, so balance and history always match.

    - quantity: whole number > 0; the type says in (receipt, adjustment_in,
      opening) or out (issue, adjustment_out) (P7).
    - A receipt must name its purchase line; other types must not.
    - Out-movements never take stock below 0 (INV-07, BR-10): 409 `insufficient_stock`.
    - The item should be locked first (lock_stock_items).
    """
    if movement_type not in MovementType.ALL:
        raise ValueError(f"Unknown stock movement type: {movement_type!r}")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("A stock movement's quantity must be a whole number above 0.")
    if (movement_type == MovementType.RECEIPT) != (purchase_line_id is not None):
        raise ValueError("A receipt movement needs its purchase line, and only a receipt has one.")
    if issued_to_employee_id is not None and movement_type != MovementType.ISSUE:
        raise ValueError("Only an issue can name the employee who received it.")
    reason = optional_text(reason)
    if reason is not None and len(reason) > REASON_MAX_LENGTH:
        raise AppError(422, "invalid_reason", f"The reason can be at most {REASON_MAX_LENGTH} characters.")

    if movement_type in MovementType.OUTGOING:
        if quantity > item.quantity_on_hand:
            raise insufficient_stock_error(item, quantity)
        new_balance = item.quantity_on_hand - quantity
    else:
        new_balance = item.quantity_on_hand + quantity

    item.quantity_on_hand = new_balance
    movement = StockMovement(
        stock_item_id=item.id,
        stock_item=item,
        movement_type=movement_type,
        quantity=quantity,
        balance_after=new_balance,
        movement_date=movement_date,
        purchase_line_id=purchase_line_id,
        reason=reason,
        issued_to_employee_id=issued_to_employee_id,
        created_by_user_id=actor.id,
    )
    db.add(movement)
    return movement


# ---- Issue and adjust (Slice 4.4: INV-04, INV-07, BR-09, BR-10, BR-13; A4, A5, A4-5a) ---------
def _today() -> date:
    """Today's date in the company timezone (Q11), as for purchase and received dates."""
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def _change_date(value: date | None) -> date:
    """The movement's business date (C2): today by default; earlier allowed; never in the future (A4-5a)."""
    if value is None:
        return _today()
    if value > _today():
        raise AppError(422, "movement_date_in_future", "The date cannot be in the future.")
    return value


def _change_reason(value: str | None) -> str:
    """Required for every issue and adjustment (Q7, C3): trimmed, up to 500 characters."""
    reason = optional_text(value)
    if reason is None:
        raise AppError(422, "invalid_reason", "Please enter the reason.")
    if len(reason) > REASON_MAX_LENGTH:
        raise AppError(422, "invalid_reason", f"The reason can be at most {REASON_MAX_LENGTH} characters.")
    return reason


def _optional_note(value: str | None) -> str | None:
    """The optional note on opening stock (A6): trimmed, up to 500 characters."""
    note = optional_text(value)
    if note is not None and len(note) > REASON_MAX_LENGTH:
        raise AppError(422, "invalid_reason", f"The note can be at most {REASON_MAX_LENGTH} characters.")
    return note


def _ensure_no_movements(db: Session, item: StockItem) -> None:
    """Opening stock is allowed once, only while the item has no movements at all (A6).
    The item row is locked, so two opening entries at the same moment cannot both pass."""
    has_any = db.scalar(select(StockMovement.id).where(StockMovement.stock_item_id == item.id).limit(1))
    if has_any is not None:
        raise AppError(
            409, "opening_stock_not_allowed",
            f'Stock item "{item.name}" already has stock movements. Opening stock can only be entered once, '
            "before any other movement; correct the balance with Adjust instead.",
        )


def _locked_usable_item(db: Session, item_id: int) -> StockItem:
    """Row-lock the item (C11) and refuse an inactive one (B38, B41)."""
    item = lock_stock_items(db, [item_id])[item_id]
    if not item.is_active:
        raise AppError(409, "stock_item_inactive", f'Stock item "{item.name}" is deactivated.')
    return item


def _issue_employee(db: Session, employee_id: int | None):
    """The optional employee an issue goes to: must exist and be active (A4, EMP-05)."""
    if employee_id is None:
        return None
    from app.modules.employees import service as employees_service

    employee = employees_service.get_employee(db, employee_id)  # 404 employee_not_found
    if not employee.is_active:
        raise AppError(
            409, "employee_inactive", f"{employee.full_name} is deactivated. Stock cannot be issued to them."
        )
    return employee


def _change_stock(
    db: Session,
    *,
    actor: User,
    item_id: int,
    movement_type: str,
    quantity: int,
    reason: str | None,
    movement_date: date | None,
    employee_id: int | None,
    action: str,
    context: AuditContext | None,
    reason_required: bool = True,
) -> tuple[StockItem, StockMovement]:
    """The one path for issues, adjustments and opening stock: lock the item, check everything, write the
    movement + new balance (record_movement) and the audit row, then commit. Any failure
    rolls everything back, so nothing is saved."""
    try:
        item = _locked_usable_item(db, item_id)
        if movement_type == MovementType.OPENING:
            _ensure_no_movements(db, item)
        employee = _issue_employee(db, employee_id)
        when = _change_date(movement_date)
        clean_reason = _change_reason(reason) if reason_required else _optional_note(reason)
        before = {"quantity_on_hand": item.quantity_on_hand}
        movement = record_movement(
            db, item=item, movement_type=movement_type, quantity=quantity, movement_date=when,
            actor=actor, reason=clean_reason, issued_to_employee_id=employee.id if employee else None,
        )
        db.flush()  # gives the movement its id for the audit row
        after = {
            "quantity_on_hand": item.quantity_on_hand,
            "movement_id": movement.id,
            "movement_type": movement_type,
            "quantity": quantity,
            "movement_date": when,
            "reason": clean_reason,
        }
        if employee is not None:
            after["issued_to"] = {"id": employee.id, "employee_code": employee.employee_code, "full_name": employee.full_name}
        audit.record(db, actor=actor, action=action, entity=item, before=before, after=after, context=context)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(item)
    db.refresh(movement)
    return item, movement


def issue_stock(
    db: Session,
    *,
    actor: User,
    item_id: int,
    quantity: int,
    reason: str | None,
    employee_id: int | None = None,
    movement_date: date | None = None,
    context: AuditContext | None = None,
) -> tuple[StockItem, StockMovement]:
    """Issue stock (INV-04, A4): an `issue` movement; never below 0 (`insufficient_stock`,
    INV-07 / BR-10); optional active employee; audit `stock.issued`."""
    return _change_stock(
        db, actor=actor, item_id=item_id, movement_type=MovementType.ISSUE, quantity=quantity, reason=reason,
        movement_date=movement_date, employee_id=employee_id, action=AuditAction.STOCK_ISSUED, context=context,
    )


def adjust_stock(
    db: Session,
    *,
    actor: User,
    item_id: int,
    direction: str,
    quantity: int,
    reason: str | None,
    movement_date: date | None = None,
    context: AuditContext | None = None,
) -> tuple[StockItem, StockMovement]:
    """Adjust stock (A5): add (`adjustment_in`) or remove (`adjustment_out`, never below 0)
    N with a required reason; audit `stock.adjusted`. No approval step (Q7)."""
    movement_type = MovementType.ADJUSTMENT_IN if direction == "add" else MovementType.ADJUSTMENT_OUT
    return _change_stock(
        db, actor=actor, item_id=item_id, movement_type=movement_type, quantity=quantity, reason=reason,
        movement_date=movement_date, employee_id=None, action=AuditAction.STOCK_ADJUSTED, context=context,
    )


def enter_opening_stock(
    db: Session,
    *,
    actor: User,
    item_id: int,
    quantity: int,
    note: str | None = None,
    movement_date: date | None = None,
    context: AuditContext | None = None,
) -> tuple[StockItem, StockMovement]:
    """Opening stock (Slice 4.5, INV-01, Q4; owner's answer A6): an `opening` movement of N
    on an ACTIVE item that has NO movements yet (else 409 `opening_stock_not_allowed`);
    optional note; audit `stock.opening`; one transaction, a failure saves nothing."""
    return _change_stock(
        db, actor=actor, item_id=item_id, movement_type=MovementType.OPENING, quantity=quantity, reason=note,
        movement_date=movement_date, employee_id=None, action=AuditAction.STOCK_OPENING, context=context,
        reason_required=False,
    )
