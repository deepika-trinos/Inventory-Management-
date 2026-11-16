"""Purchases: list, get, create, edit, cancel (Slice 3.1, PUR-01 to PUR-04, PUR-08, BR-06)
and receive them: one-by-one items (Slice 3.2, PUR-05, PUR-06, BR-07, BR-08) and
by-quantity items (Slice 3.3, PUR-07, INV-03).

Used by the /purchases endpoints (Admin and IT Manager, P6). Slice 3.4 adds the
purchase history screens.

Every change writes an audit row in the SAME transaction (BR-13, B11).

RULES
- A new purchase is a DRAFT. Drafts and cancelled purchases NEVER change stock or
  create assets (PUR-08, BR-06): only receive_purchase() does.
- Only a DRAFT can be edited or cancelled (`purchase_not_draft`). Cancelled and
  received are final (P6).
- Vendor must be ACTIVE (vendors.ensure_vendor_active, B33). Reference number is
  required and unique per vendor ignoring case among purchases that are not
  cancelled (P3, B43). Purchase date cannot be in the future, in the company
  timezone (P3, Q11).
- At least one line; serialized and bulk lines may be mixed (P1):
    bulk       -> an ACTIVE stock item (inventory.ensure_stock_item_usable, B41)
    serialized -> an ACTIVE category tracked one by one
                  (categories.ensure_category_selectable, B13) + a description.
- Edits check only what changed (B45): the vendor is checked when it is changed;
  a line's stock item / category is checked when it was not already on the draft.
  Lines sent in an edit REPLACE all the draft's lines.
- Line totals and the purchase total are calculated here, never typed in.
- BR-12: purchases are never deleted. There is no delete function and no DELETE endpoint.

RECEIVING (Slices 3.2-3.3, see receive_purchase)
- Only a DRAFT is received, in ONE step covering every line, one-by-one and
  by-quantity mixed (B55). It then becomes RECEIVED and is final (P6).
- Per line: received quantity 0 to ordered (P4); at least 1 unit in total (B58).
  Received date: not before the purchase date, not in the future (B58).
- One-by-one line: one asset per unit received (PUR-06, BR-08), status
  Available, IDs AST-000001...
- By-quantity line: one `receipt` stock movement of the received quantity,
  raising the stock item's balance (PUR-07, INV-03). 0 received = no movement
  (C1). The stock items are row-locked first, so receipts saved at the same
  moment add up correctly. A DEACTIVATED stock item refuses the receipt when
  stock would arrive (`stock_item_inactive`, C5, keeps B38 true).
- A deactivated vendor or category does not block receiving (B59).
- Everything (status, quantities, assets, movements, balances, audit rows) in
  ONE transaction: any failure (e.g. a duplicate serial number) saves nothing.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.core.text import optional_text, required_text
from app.modules.assets import service as assets_service
from app.modules.assets.models import Asset, AssetStatus
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.categories import service as categories_service
from app.modules.categories.models import TrackingType
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import MovementType, StockItem
from app.modules.purchases.models import LineType, Purchase, PurchaseLine, PurchaseStatus
from app.modules.purchases.schemas import MAX_UNITS_PER_RECEIPT
from app.modules.users.models import User
from app.modules.vendors import service as vendors_service
from app.modules.vendors.models import Vendor

# Fields the purchase list can be sorted by.
_SORTABLE = {
    "purchase_number": Purchase.id,  # numbers are given out in order
    "purchase_date": Purchase.purchase_date,
    "reference_number": func.lower(Purchase.reference_number),
    "vendor": func.lower(Vendor.name),
    "status": Purchase.status,
    "created_at": Purchase.created_at,
    "updated_at": Purchase.updated_at,
}

# Name of the partial unique index on (vendor_id, lower(reference_number)) (migration 0008).
_REFERENCE_INDEX = "uq_purchases_vendor_reference_lower"


# ---- Small helpers ------------------------------------------------------------------
def _reference_taken_error() -> AppError:
    return AppError(
        409,
        "purchase_reference_taken",
        "This vendor already has a purchase with this invoice / reference number.",
    )


def _today() -> date:
    """Today's date in the company timezone (Q11)."""
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def _check_purchase_date(value: date) -> date:
    if value > _today():
        raise AppError(422, "purchase_date_in_future", "The purchase date cannot be in the future.")
    return value


def _clean_reference(value: str) -> str:
    return required_text(value, "invalid_reference", "Please enter the invoice / reference number.")


def _line_error(status_code: int, code: str, number: int, message: str) -> AppError:
    return AppError(status_code, code, f"Line {number}: {message}", {"line": number})


def _with_line(error: AppError, number: int) -> AppError:
    """Add the line number to an error raised by another module's helper."""
    details = error.details if isinstance(error.details, dict) else {}
    return AppError(error.status_code, error.code, f"Line {number}: {error.message}", {**details, "line": number})


def _ensure_reference_free(db: Session, vendor_id: int, reference: str, *, except_id: int | None = None) -> None:
    clash = db.scalar(
        select(Purchase.id).where(
            Purchase.vendor_id == vendor_id,
            func.lower(Purchase.reference_number) == reference.lower(),
            Purchase.status != PurchaseStatus.CANCELLED,
        )
    )
    if clash is not None and clash != except_id:
        raise _reference_taken_error()


def _ensure_draft(purchase: Purchase, doing: str) -> None:
    if not purchase.is_draft:
        raise AppError(
            409,
            "purchase_not_draft",
            f"Only a draft purchase can be {doing}. {purchase.purchase_number} is {purchase.status}.",
        )


def _line_snapshot(line: PurchaseLine) -> dict[str, Any]:
    return {
        "line_type": line.line_type,
        "stock_item_id": line.stock_item_id,
        "stock_item": line.stock_item.name if line.stock_item else None,
        "category_id": line.category_id,
        "category": line.category.name if line.category else None,
        "description": line.description,
        "quantity": line.quantity,
        "unit_cost": Decimal(line.unit_cost).quantize(Decimal("0.01")),
        "line_total": line.line_total,
        "received_quantity": line.received_quantity,
        "asset_codes": [asset.asset_code for asset in line.assets],
    }


def _bulk_receipt_snapshot(line: PurchaseLine, balance_after: int | None) -> dict[str, Any]:
    """What purchase.received records about a by-quantity line (C8): item, quantity, new balance."""
    return {
        "stock_item_id": line.stock_item_id,
        "stock_item": line.stock_item.name if line.stock_item else None,
        "unit_of_measure": line.stock_item.unit_of_measure if line.stock_item else None,
        "received_quantity": line.received_quantity,
        "balance_after": balance_after,
    }


def _snapshot(purchase: Purchase) -> dict[str, Any]:
    """What the audit log records about a purchase (with its lines and calculated total)."""
    return {
        "purchase_number": purchase.purchase_number,
        "vendor_id": purchase.vendor_id,
        "vendor": purchase.vendor.name if purchase.vendor else None,
        "reference_number": purchase.reference_number,
        "purchase_date": purchase.purchase_date,
        "received_date": purchase.received_date,
        "notes": purchase.notes,
        "status": purchase.status,
        "total_amount": purchase.total_amount,
        "lines": [_line_snapshot(line) for line in purchase.lines],
    }


def _line_key(line: PurchaseLine) -> tuple:
    """What makes two lines the same (to spot an edit that changes nothing)."""
    return (
        line.line_type,
        line.stock_item_id,
        line.category_id,
        line.description,
        line.quantity,
        Decimal(line.unit_cost).quantize(Decimal("0.01")),
    )


def _build_lines(
    db: Session,
    lines: list[dict[str, Any]],
    *,
    known_stock_items: frozenset[int] = frozenset(),
    known_categories: frozenset[int] = frozenset(),
) -> list[PurchaseLine]:
    """Check each line and turn it into a PurchaseLine (not yet added to the session).

    A stock item or category that is already on the draft (`known_*`) is not
    re-checked for being active (B45): only what changed is checked.
    """
    if not lines:
        raise AppError(422, "lines_required", "Add at least one line to the purchase.")
    built: list[PurchaseLine] = []
    for number, data in enumerate(lines, start=1):
        line_type = data["line_type"]
        stock_item_id = data.get("stock_item_id")
        category_id = data.get("category_id")
        description = optional_text(data.get("description"))
        quantity = data["quantity"]
        unit_cost = Decimal(data["unit_cost"]).quantize(Decimal("0.01"))

        if line_type == LineType.BULK:
            if stock_item_id is None:
                raise _line_error(422, "invalid_line", number, "choose the stock item for a by-quantity line.")
            if category_id is not None or description is not None:
                raise _line_error(
                    422,
                    "invalid_line",
                    number,
                    "a by-quantity line takes a stock item only (no category or description).",
                )
            try:
                if stock_item_id in known_stock_items:
                    item = inventory_service.get_stock_item(db, stock_item_id)
                else:
                    item = inventory_service.ensure_stock_item_usable(db, stock_item_id)  # stock_item_inactive
            except AppError as error:
                raise _with_line(error, number) from None
            built.append(
                PurchaseLine(
                    line_type=line_type, stock_item=item, stock_item_id=item.id,
                    quantity=quantity, unit_cost=unit_cost,
                )
            )
        else:  # serialized
            if category_id is None:
                raise _line_error(422, "invalid_line", number, "choose the category for a one-by-one line.")
            if stock_item_id is not None:
                raise _line_error(
                    422,
                    "invalid_line",
                    number,
                    "a one-by-one line takes a category and a description, not a stock item.",
                )
            if description is None:
                raise _line_error(
                    422, "invalid_line", number, 'describe the item, e.g. "Laptops: Dell Latitude 5440".'
                )
            try:
                category = categories_service.get_category(db, category_id)
                if category.tracking_type != TrackingType.SERIALIZED:
                    raise AppError(
                        409,
                        "category_not_serialized",
                        f'Category "{category.name}" is tracked by quantity. '
                        "Use a by-quantity line with one of its stock items instead.",
                    )
                if category_id not in known_categories:
                    categories_service.ensure_category_selectable(db, category_id)  # category_inactive
            except AppError as error:
                raise _with_line(error, number) from None
            built.append(
                PurchaseLine(
                    line_type=line_type, category=category, category_id=category.id, description=description,
                    quantity=quantity, unit_cost=unit_cost,
                )
            )
    return built


def _save(
    db: Session,
    *,
    actor: User,
    action: str,
    purchase: Purchase,
    before: dict[str, Any] | None,
    context: AuditContext | None,
) -> Purchase:
    """Write the audit row and commit the change together; undo both on any error."""
    try:
        db.flush()
        audit.record(
            db, actor=actor, action=action, entity=purchase, before=before, after=_snapshot(purchase), context=context
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Two people saving the same reference at the same moment: the unique index wins.
        if _REFERENCE_INDEX in str(exc.orig):
            raise _reference_taken_error() from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(purchase)
    return purchase


# ---- Reading ----------------------------------------------------------------------
def get_purchase(db: Session, purchase_id: int, *, lock: bool = False) -> Purchase:
    """One purchase with its lines. lock=True holds a row lock until commit, so two
    people cannot edit / cancel (or, later, receive) the same purchase at once."""
    if lock:
        found = db.scalar(select(Purchase.id).where(Purchase.id == purchase_id).with_for_update())
        if found is None:
            raise AppError(404, "purchase_not_found", "Purchase not found.")
        return db.get(Purchase, purchase_id, populate_existing=True)
    purchase = db.get(Purchase, purchase_id)
    if purchase is None:
        raise AppError(404, "purchase_not_found", "Purchase not found.")
    return purchase


def list_purchases(
    db: Session,
    params: PageParams,
    *,
    search: str | None = None,
    status: str | None = None,
    vendor_id: int | None = None,
) -> dict[str, Any]:
    """Paged list. `search` matches part of the reference number, the vendor's
    name or the purchase number, ignoring case."""
    stmt: Select = select(Purchase).join(Vendor, Purchase.vendor_id == Vendor.id)
    if search and search.strip():
        term = search.strip().lower()
        stmt = stmt.where(
            or_(
                func.lower(Purchase.reference_number).contains(term, autoescape=True),
                func.lower(Vendor.name).contains(term, autoescape=True),
                func.lower(Purchase.purchase_number).contains(term, autoescape=True),
            )
        )
    if status:
        stmt = stmt.where(Purchase.status == status)
    if vendor_id is not None:
        stmt = stmt.where(Purchase.vendor_id == vendor_id)
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="-purchase_number")


# ---- Changing ---------------------------------------------------------------------
def create_purchase(
    db: Session,
    *,
    data: dict[str, Any],
    actor: User,
    context: AuditContext | None = None,
) -> Purchase:
    """Create a DRAFT purchase with its lines (audit: purchase.created).
    Changes no stock and creates no assets (PUR-08, BR-06)."""
    vendor = vendors_service.ensure_vendor_active(db, data["vendor_id"])  # vendor_inactive
    reference = _clean_reference(data["reference_number"])
    purchase_date = _check_purchase_date(data["purchase_date"])
    lines = _build_lines(db, data.get("lines") or [])
    _ensure_reference_free(db, vendor.id, reference)

    purchase = Purchase(
        vendor=vendor,
        vendor_id=vendor.id,
        reference_number=reference,
        purchase_date=purchase_date,
        notes=optional_text(data.get("notes")),
        status=PurchaseStatus.DRAFT,
        created_by_user_id=actor.id,
        lines=lines,
    )
    db.add(purchase)
    return _save(db, actor=actor, action=AuditAction.PURCHASE_CREATED, purchase=purchase, before=None, context=context)


def update_purchase(
    db: Session,
    *,
    actor: User,
    purchase: Purchase,
    changes: dict[str, Any],
    context: AuditContext | None = None,
) -> Purchase:
    """Edit a DRAFT (audit: purchase.updated, only when something really changed).

    `changes` holds only the fields actually sent. `lines`, when sent, replaces all
    lines. Only what changed is checked (B45). Changes no stock (PUR-08, BR-06).
    """
    _ensure_draft(purchase, "edited")
    before = _snapshot(purchase)
    new: dict[str, Any] = {}

    vendor_id = changes.get("vendor_id")
    if vendor_id is not None and vendor_id != purchase.vendor_id:
        new["vendor"] = vendors_service.ensure_vendor_active(db, vendor_id)  # vendor_inactive
        new["vendor_id"] = vendor_id
    if changes.get("reference_number") is not None:
        reference = _clean_reference(changes["reference_number"])
        if reference != purchase.reference_number:
            new["reference_number"] = reference
    if changes.get("purchase_date") is not None and changes["purchase_date"] != purchase.purchase_date:
        new["purchase_date"] = _check_purchase_date(changes["purchase_date"])
    if "notes" in changes:
        notes = optional_text(changes["notes"])
        if notes != purchase.notes:
            new["notes"] = notes

    new_lines: list[PurchaseLine] | None = None
    if changes.get("lines") is not None:
        candidate = _build_lines(
            db,
            changes["lines"],
            known_stock_items=frozenset(line.stock_item_id for line in purchase.lines if line.stock_item_id),
            known_categories=frozenset(line.category_id for line in purchase.lines if line.category_id),
        )
        if [_line_key(line) for line in candidate] != [_line_key(line) for line in purchase.lines]:
            new_lines = candidate

    if not new and new_lines is None:
        return purchase  # nothing to save or record

    target_vendor = new.get("vendor_id", purchase.vendor_id)
    target_reference = new.get("reference_number", purchase.reference_number)
    if "vendor_id" in new or target_reference.lower() != purchase.reference_number.lower():
        _ensure_reference_free(db, target_vendor, target_reference, except_id=purchase.id)

    for field, value in new.items():
        setattr(purchase, field, value)
    if new_lines is not None:
        purchase.lines = new_lines  # the old line rows are deleted (draft only)
    return _save(
        db, actor=actor, action=AuditAction.PURCHASE_UPDATED, purchase=purchase, before=before, context=context
    )


def cancel_purchase(
    db: Session,
    *,
    actor: User,
    purchase: Purchase,
    context: AuditContext | None = None,
) -> Purchase:
    """Cancel a DRAFT (audit: purchase.cancelled). Final: a cancelled purchase can
    never be edited, received or reopened. Nothing is deleted; no stock changes.
    Allowed even if the vendor or items have been deactivated since."""
    _ensure_draft(purchase, "cancelled")
    before = _snapshot(purchase)
    purchase.status = PurchaseStatus.CANCELLED
    return _save(
        db, actor=actor, action=AuditAction.PURCHASE_CANCELLED, purchase=purchase, before=before, context=context
    )


# ---- Receiving (Slice 3.2: one-by-one items, Slice 3.3: by-quantity items) ------------

def _unit_error(error: AppError, line_number: int, unit_number: int) -> AppError:
    """Add where the unit is (line 1, 2, ... and unit 1, 2, ...) to an error."""
    details = error.details if isinstance(error.details, dict) else {}
    return AppError(
        error.status_code,
        error.code,
        f"Line {line_number}, unit {unit_number}: {error.message}",
        {**details, "line": line_number, "unit": unit_number},
    )


def _check_received_date(purchase: Purchase, value: date) -> date:
    if value > _today():
        raise AppError(422, "received_date_in_future", "The received date cannot be in the future.")
    if value < purchase.purchase_date:
        raise AppError(
            422,
            "received_date_before_purchase",
            f"The received date cannot be before the purchase date ({purchase.purchase_date.isoformat()}).",
        )
    return value


def _match_receipt_lines(purchase: Purchase, sent: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Every line of the purchase must be sent exactly once, and nothing else (B55)."""
    own_ids = {line.id for line in purchase.lines}
    by_id: dict[int, dict[str, Any]] = {}
    for item in sent:
        line_id = item["line_id"]
        if line_id not in own_ids:
            raise AppError(
                422,
                "invalid_receipt_line",
                f"Line id {line_id} is not part of {purchase.purchase_number}.",
                {"line_id": line_id},
            )
        if line_id in by_id:
            raise AppError(422, "invalid_receipt_line", f"Line id {line_id} was sent twice.", {"line_id": line_id})
        by_id[line_id] = item
    for number, line in enumerate(purchase.lines, start=1):
        if line.id not in by_id:
            raise _line_error(422, "receipt_line_missing", number, "say how many units arrived (0 if none).")
    return by_id


def _check_receipt(
    db: Session, purchase: Purchase, sent: dict[int, dict[str, Any]], stock_items: dict[int, StockItem]
) -> list[tuple[PurchaseLine, int, list[dict[str, Any]]]]:
    """Check every line and unit BEFORE anything changes. Returns, per line:
    (line, received quantity, the cleaned details of each unit; empty for by-quantity lines).
    `stock_items` are the (locked, fresh) stock items of the by-quantity lines."""
    plan: list[tuple[PurchaseLine, int, list[dict[str, Any]]]] = []
    seen: dict[str, tuple[int, int]] = {}  # lower(serial) -> (line, unit) where it was first typed
    total_units = 0  # assets to create (limited by MAX_UNITS_PER_RECEIPT)
    total_received = 0  # assets + by-quantity units
    for number, line in enumerate(purchase.lines, start=1):
        item = sent[line.id]
        quantity = item["received_quantity"]
        units = item.get("units") or []
        if quantity > line.quantity:
            raise _line_error(
                422,
                "received_quantity_too_high",
                number,
                f"{quantity} received but only {line.quantity} ordered. More than ordered is not allowed.",
            )
        total_received += quantity

        if line.line_type == LineType.BULK:
            if units:
                raise _line_error(
                    422,
                    "units_not_allowed",
                    number,
                    "a by-quantity line takes a received quantity only, no unit details.",
                )
            stock_item = stock_items[line.stock_item_id]
            if quantity > 0 and not stock_item.is_active:
                raise _line_error(
                    409,
                    "stock_item_inactive",
                    number,
                    f'stock item "{stock_item.name}" is deactivated. Reactivate it first, then receive.',
                )
            plan.append((line, quantity, []))
            continue

        if len(units) != quantity:
            raise _line_error(
                422,
                "unit_count_mismatch",
                number,
                f"{quantity} received, so enter the details of {quantity} unit(s) (got {len(units)}).",
            )
        total_units += quantity
        if total_units > MAX_UNITS_PER_RECEIPT:
            raise AppError(422, "too_many_units", f"One receipt can create at most {MAX_UNITS_PER_RECEIPT} assets.")

        cleaned: list[dict[str, Any]] = []
        for unit_number, unit in enumerate(units, start=1):
            try:
                clean = assets_service.clean_unit(
                    unit, default_name=line.description, purchase_date=purchase.purchase_date
                )
            except AppError as error:
                raise _unit_error(error, number, unit_number) from None
            key = clean["serial_number"].lower()
            if key in seen:
                first_line, first_unit = seen[key]
                duplicate = AppError(
                    409,
                    "serial_number_duplicate",
                    f'serial number "{clean["serial_number"]}" is entered twice in this receipt '
                    f"(also line {first_line}, unit {first_unit}).",
                    {"other_line": first_line, "other_unit": first_unit},
                )
                raise _unit_error(duplicate, number, unit_number)
            seen[key] = (number, unit_number)
            cleaned.append(clean)
        plan.append((line, quantity, cleaned))

    if total_received == 0:
        raise AppError(422, "nothing_received", "Nothing was received. At least one unit must arrive.")

    # Serial numbers already used by existing assets (AST-06): point at the first one.
    in_use = assets_service.serials_in_use(db, seen.keys())
    for number, (_line, _quantity, cleaned) in enumerate(plan, start=1):
        for unit_number, clean in enumerate(cleaned, start=1):
            if clean["serial_number"].lower() in in_use:
                raise _unit_error(assets_service.serial_taken_error(clean["serial_number"]), number, unit_number)
    return plan


def receive_purchase(
    db: Session,
    *,
    actor: User,
    purchase: Purchase,
    data: dict[str, Any],
    context: AuditContext | None = None,
) -> Purchase:
    """Receive a DRAFT purchase in ONE step, every line (Slices 3.2-3.3, B55).

    data = {"received_date": date, "lines": [{"line_id", "received_quantity",
            "units": [{"serial_number", "model", "name", "brand", "warranty_expiry", "location"}]}]}
    By-quantity lines send no units.

    One-by-one line: one asset per unit received (PUR-06, BR-08), status
    Available, with the line's category, the purchase date and the line's unit
    cost (AST-02). By-quantity line: one `receipt` stock movement (dated the
    received date) raising the stock item's balance (PUR-07, INV-03); none when
    0 arrived (C1). The purchase becomes RECEIVED (final, P6).
    Audit: purchase.received (listing the by-quantity receipts with each new
    balance) plus one asset.created per asset; no audit row per movement (the
    movement table is itself the permanent history). All in ONE transaction:
    any failure saves nothing.

    The caller must hold the purchase's row lock (get_purchase(lock=True)).

    Errors: 409 `purchase_not_draft`, `stock_item_inactive` (C5),
    `serial_number_duplicate` (same serial twice in this receipt),
    `serial_number_taken` (an existing asset has it);
    422 `received_date_in_future`, `received_date_before_purchase`,
    `invalid_receipt_line`, `receipt_line_missing`, `received_quantity_too_high`,
    `unit_count_mismatch`, `units_not_allowed`, `nothing_received`, `too_many_units`,
    `invalid_serial_number`, `invalid_model`, `invalid_asset_name`, `invalid_brand`,
    `invalid_location`, `invalid_warranty_expiry`. Line / unit problems carry
    details.line and details.unit (1, 2, ...).
    """
    _ensure_draft(purchase, "received")

    received_date = _check_received_date(purchase, data["received_date"])
    sent = _match_receipt_lines(purchase, data.get("lines") or [])
    # Lock the stock items now (id order) and read their CURRENT status and balance.
    stock_items = inventory_service.lock_stock_items(
        db, {line.stock_item_id for line in purchase.lines if line.line_type == LineType.BULK}
    )
    plan = _check_receipt(db, purchase, sent, stock_items)

    # Everything checked: apply the receipt.
    before = _snapshot(purchase)
    new_assets: list[Asset] = []
    bulk_receipts: list[dict[str, Any]] = []
    for line, quantity, cleaned in plan:
        line.received_quantity = quantity
        if line.line_type == LineType.BULK:
            balance = None
            if quantity > 0:
                movement = inventory_service.record_movement(
                    db,
                    item=stock_items[line.stock_item_id],
                    movement_type=MovementType.RECEIPT,
                    quantity=quantity,
                    movement_date=received_date,
                    actor=actor,
                    purchase_line_id=line.id,
                )
                balance = movement.balance_after
            bulk_receipts.append(_bulk_receipt_snapshot(line, balance))
            continue
        for clean in cleaned:
            asset = Asset(
                **clean,
                category_id=line.category_id,
                category=line.category,
                purchase_line=line,
                purchase_date=purchase.purchase_date,
                cost=line.unit_cost,
                status=AssetStatus.AVAILABLE,
                created_by_user_id=actor.id,
            )
            db.add(asset)
            new_assets.append(asset)
    purchase.received_date = received_date
    purchase.status = PurchaseStatus.RECEIVED

    try:
        db.flush()  # the database gives each asset its AST-... ID here
        after = _snapshot(purchase)
        if bulk_receipts:
            after["stock_received"] = bulk_receipts
        audit.record(
            db,
            actor=actor,
            action=AuditAction.PURCHASE_RECEIVED,
            entity=purchase,
            before=before,
            after=after,
            context=context,
        )
        for asset in new_assets:
            audit.record(
                db,
                actor=actor,
                action=AuditAction.ASSET_CREATED,
                entity=asset,
                before=None,
                after=assets_service.snapshot(asset),
                context=context,
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Two receipts saving the same serial number at the same moment: the unique index wins.
        if assets_service.SERIAL_INDEX in str(exc.orig):
            raise assets_service.serial_taken_error() from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(purchase)
    return purchase
