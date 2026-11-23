"""Assets: the asset register (list, search, filters, one asset and its history;
Slice 4.1), editing and retiring (Slice 4.2), and the shared checks used when
assets are created (Slice 3.2: receiving a purchase; Slice 4.5 will reuse them).

RULES (AST-01, AST-02, AST-06, BR-01, P5)
- The asset ID (AST-000001, ...) is made by the database sequence: never typed.
- Serial number and model are required; brand, warranty expiry and location
  (typed text, Q1) are optional. Warranty expiry, when given, is not before the
  purchase date (B61). Text is trimmed; empty optional text is stored as empty (NULL).
- Serial numbers are unique across ALL assets ignoring case. The service checks
  first to give a clear error; the unique index uq_assets_serial_number_lower is
  the final guard when two receipts are saved at the same moment.
- Assets are never deleted (BR-12). There is no delete function and no DELETE endpoint.

EDITING AND RETIRING (Slice 4.2, AST-04, AST-07, BR-13; owner's answers A2, A3)
- Editable: name, brand, model, serial number (still unique), location, warranty
  expiry (still not before the purchase date, B61). Category, purchase date and
  cost are locked on RECEIVED assets (they come from the invoice) and editable on
  assets ENTERED BY HAND (Slice 4.5, I4). Asset ID, status and the purchase link are
  never edited: status changes only through actions (AST-07).

MANUAL ENTRY (Slice 4.5, AST-01, Q4; owner's answer A7)
- An active one-by-one category, serial number (unique), model and name required;
  brand, location, warranty, purchase date (not in the future) and cost optional; no
  purchase link or vendor; always Available. Same asset ID sequence and serial
  check as receiving. Audit asset.created in the same transaction.
- Retire only from Available or Damaged, with a required reason (free text, up
  to 500 characters). Retiring cannot be undone; a retired asset is read-only.
- Every change writes its audit row in the same transaction (asset.updated with
  the old and new value of each changed field; asset.retired with the reason).
  A failure saves nothing.
"""

from collections.abc import Iterable
from datetime import date
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.audit.models import AuditLog
from app.modules.categories import service as categories_service
from app.modules.categories.models import AssetCategory
from app.modules.users.models import User
from app.modules.assets.models import (
    ASSET_CODE_PREFIX,
    BRAND_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    MODEL_MAX_LENGTH,
    NAME_MAX_LENGTH,
    RETIRE_REASON_MAX_LENGTH,
    SERIAL_MAX_LENGTH,
    Asset,
    AssetStatus,
)

# Name of the unique index on lower(serial_number) (migration 0009).
SERIAL_INDEX = "uq_assets_serial_number_lower"


def serial_taken_error(serial: str | None = None) -> AppError:
    if serial:
        message = f'Serial number "{serial}" is already used by another asset.'
    else:
        message = "One of these serial numbers is already used by another asset."
    return AppError(409, "serial_number_taken", message)


# ---- Reading ----------------------------------------------------------------------
def get_asset(db: Session, ref: str | int) -> Asset:
    """One asset by its id (e.g. 7) or its asset ID (e.g. "AST-000007", any case)."""
    text = str(ref).strip()
    asset: Asset | None = None
    if text.isdigit():
        asset = db.get(Asset, int(text))
    elif text.upper().startswith(ASSET_CODE_PREFIX):
        asset = db.scalar(select(Asset).where(Asset.asset_code == text.upper()))
    if asset is None:
        raise AppError(404, "asset_not_found", "Asset not found.")
    return asset


# Columns the register can be sorted by. Text is sorted ignoring upper/lower case.
# Rows with the same value are ordered by id in the same direction, so paging never
# repeats or skips a row.
_SORTABLE = {
    "asset_code": Asset.asset_code,
    "name": func.lower(Asset.name),
    "category": func.lower(AssetCategory.name),
    "brand": func.lower(Asset.brand),
    "model": func.lower(Asset.model),
    "serial_number": func.lower(Asset.serial_number),
    "status": Asset.status,
    "location": func.lower(Asset.location),
    "warranty_expiry": Asset.warranty_expiry,
    "created_at": Asset.created_at,
}


def list_assets(
    db: Session,
    params: PageParams,
    *,
    search: str | None = None,
    category_id: int | None = None,
    status: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """The asset register (AST-03, AST-05): one sorted page of assets.

    - `search` matches part of the asset ID, serial number or name, ignoring case.
    - `category_id`: one category (active or inactive). Unknown: 404 `category_not_found`.
    - `status`: one asset status (PRD 8.1).
    - `location`: the whole location, ignoring case (typed text, Q1; like department, B23).
    All filters combine (every one must match).
    """
    stmt: Select = select(Asset).join(AssetCategory, Asset.category_id == AssetCategory.id)
    if search and search.strip():
        term = search.strip().lower()
        stmt = stmt.where(
            func.lower(Asset.asset_code).contains(term, autoescape=True)
            | func.lower(Asset.serial_number).contains(term, autoescape=True)
            | func.lower(Asset.name).contains(term, autoescape=True)
        )
    if category_id is not None:
        categories_service.get_category(db, category_id)  # 404 for an unknown category
        stmt = stmt.where(Asset.category_id == category_id)
    if status:
        stmt = stmt.where(Asset.status == status)
    if location and location.strip():
        stmt = stmt.where(func.lower(Asset.location) == location.strip().lower())
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="-asset_code", tiebreaker=Asset.id)


def list_locations(db: Session) -> list[str]:
    """Every location already typed on an asset, A-Z, one spelling per location
    ignoring case (for the location filter)."""
    rows = db.scalars(
        select(func.min(Asset.location))
        .where(Asset.location.is_not(None))
        .group_by(func.lower(Asset.location))
        .order_by(func.lower(Asset.location))
    )
    return [r for r in rows if r]


def asset_history(db: Session, asset: Asset, params: PageParams) -> dict[str, Any]:
    """The asset's history: every audit log row about this asset (entity "assets"),
    newest first, with who did it. Later slices (edit / retire, assign / return,
    maintenance) add their own rows here automatically (BR-13)."""
    stmt = select(AuditLog).where(AuditLog.entity_type == Asset.__tablename__, AuditLog.entity_id == str(asset.id))
    page = paginate(
        db, stmt, params, sortable={"created_at": AuditLog.created_at}, default_sort="-created_at", tiebreaker=AuditLog.id
    )
    actor_ids = {row.actor_user_id for row in page["items"] if row.actor_user_id is not None}
    actors = {u.id: u for u in db.scalars(select(User).where(User.id.in_(actor_ids)))} if actor_ids else {}
    page["items"] = [
        {
            "id": row.id,
            "action": row.action,
            "created_at": row.created_at,
            "actor": actors.get(row.actor_user_id),
            "before": row.before_data,
            "after": row.after_data,
        }
        for row in page["items"]
    ]
    return page


def purchase_summary(asset: Asset) -> dict[str, Any] | None:
    """Where the asset came from, for the API response (None when entered by hand)."""
    line = asset.purchase_line
    if line is None:
        return None
    purchase = line.purchase
    return {
        "purchase_id": purchase.id,
        "purchase_number": purchase.purchase_number,
        "purchase_line_id": line.id,
        "vendor_id": purchase.vendor_id,
        "vendor": purchase.vendor.name,
        "reference_number": purchase.reference_number,
    }


def snapshot(asset: Asset) -> dict[str, Any]:
    """What the audit log records about an asset (asset.created)."""
    line = asset.purchase_line
    return {
        "asset_code": asset.asset_code,
        "name": asset.name,
        "category_id": asset.category_id,
        "category": asset.category.name if asset.category else None,
        "brand": asset.brand,
        "model": asset.model,
        "serial_number": asset.serial_number,
        "status": asset.status,
        "location": asset.location,
        "warranty_expiry": asset.warranty_expiry,
        "purchase_number": line.purchase.purchase_number if line is not None else None,
        "purchase_line_id": asset.purchase_line_id,
        "purchase_date": asset.purchase_date,
        "cost": asset.cost,
    }


# ---- Checks shared by everything that creates assets --------------------------------------
def _text(value: str | None, *, required: bool, max_length: int, code: str, label: str) -> str | None:
    value = (value or "").strip()
    if not value:
        if required:
            raise AppError(422, code, f"Please enter the {label}.")
        return None
    if len(value) > max_length:
        raise AppError(422, code, f"The {label} can be at most {max_length} characters.")
    return value


def clean_unit(
    data: dict[str, Any], *, default_name: str | None = None, purchase_date: date | None = None
) -> dict[str, Any]:
    """Check and tidy the typed-in details of ONE asset (P5).

    Warranty expiry is optional, but when given it cannot be before the purchase
    date (B61): "2019" typed for "2029" is caught.

    Errors: 422 `invalid_serial_number`, `invalid_model`, `invalid_asset_name`,
    `invalid_brand`, `invalid_location`, `invalid_warranty_expiry`.
    The caller adds where the unit is (line / unit).
    """
    warranty_expiry = data.get("warranty_expiry")
    if warranty_expiry is not None and purchase_date is not None and warranty_expiry < purchase_date:
        raise AppError(
            422,
            "invalid_warranty_expiry",
            f"The warranty expiry cannot be before the purchase date ({purchase_date.isoformat()}).",
        )
    name = _text(data.get("name"), required=False, max_length=NAME_MAX_LENGTH, code="invalid_asset_name", label="asset name")
    name = name or _text(default_name, required=True, max_length=NAME_MAX_LENGTH, code="invalid_asset_name", label="asset name")
    return {
        "serial_number": _text(
            data.get("serial_number"), required=True, max_length=SERIAL_MAX_LENGTH,
            code="invalid_serial_number", label="serial number",
        ),
        "model": _text(data.get("model"), required=True, max_length=MODEL_MAX_LENGTH, code="invalid_model", label="model"),
        "name": name,
        "brand": _text(data.get("brand"), required=False, max_length=BRAND_MAX_LENGTH, code="invalid_brand", label="brand"),
        "location": _text(
            data.get("location"), required=False, max_length=LOCATION_MAX_LENGTH, code="invalid_location", label="location"
        ),
        "warranty_expiry": warranty_expiry,
    }


def serials_in_use(db: Session, serials: Iterable[str]) -> set[str]:
    """The given serial numbers that existing assets already use (lower case)."""
    wanted = {s.lower() for s in serials}
    if not wanted:
        return set()
    found = db.scalars(select(func.lower(Asset.serial_number)).where(func.lower(Asset.serial_number).in_(wanted)))
    return set(found)


# ---- Manual entry (Slice 4.5) ------------------------------------------------------------
def _company_today() -> date:
    """Today in the company timezone (Q11), as for purchase dates (B48)."""
    from app.modules.inventory.service import _today

    return _today()


def _manual_purchase_date(value: date | None) -> date | None:
    if value is not None and value > _company_today():
        raise AppError(422, "purchase_date_in_future", "The purchase date cannot be in the future.")
    return value


def _manual_category(db: Session, category_id: int) -> AssetCategory:
    """An ACTIVE category tracked ONE BY ONE (B13, PRD 9.2): 404 / 409 otherwise."""
    from app.modules.categories.models import TrackingType

    category = categories_service.get_category(db, category_id)  # 404 category_not_found
    if category.tracking_type != TrackingType.SERIALIZED:
        raise AppError(
            409, "category_not_serialized",
            f'Category "{category.name}" is tracked by quantity. Enter its stock as opening stock on the Inventory page instead.',
        )
    return categories_service.ensure_category_selectable(db, category_id)  # 409 category_inactive


def create_asset(db: Session, *, actor: User, data: dict[str, Any], context: AuditContext | None = None) -> Asset:
    """Enter an asset the company already owns (A7). One transaction with asset.created;
    a failure saves nothing."""
    try:
        category = _manual_category(db, data["category_id"])
        purchase_date = _manual_purchase_date(data.get("purchase_date"))
        unit = clean_unit(data, purchase_date=purchase_date)  # serial, model, name, brand, location, warranty (P5, B61)
        if serials_in_use(db, [unit["serial_number"]]):
            raise serial_taken_error(unit["serial_number"])
        asset = Asset(
            **unit,
            category_id=category.id,
            purchase_line_id=None,
            purchase_date=purchase_date,
            cost=data.get("cost"),
            status=AssetStatus.AVAILABLE,
            created_by_user_id=actor.id,
        )
        db.add(asset)
        db.flush()
        audit.record(db, actor=actor, action=AuditAction.ASSET_CREATED, entity=asset, after=snapshot(asset), context=context)
    except Exception:
        db.rollback()
        raise
    _commit(db)
    db.refresh(asset)
    return asset


# ---- Editing and retiring (Slice 4.2) ----------------------------------------------------
EDITABLE_FIELDS = ("name", "brand", "model", "serial_number", "location", "warranty_expiry")
MANUAL_ONLY_FIELDS = ("category_id", "purchase_date", "cost")  # Slice 4.5, I4
RETIRABLE_STATUSES = (AssetStatus.AVAILABLE, AssetStatus.DAMAGED)  # A3

_STATUS_LABELS = {
    AssetStatus.AVAILABLE: "Available",
    AssetStatus.ASSIGNED: "Assigned",
    AssetStatus.UNDER_MAINTENANCE: "Under Maintenance",
    AssetStatus.DAMAGED: "Damaged",
    AssetStatus.RETIRED: "Retired",
}
_NOT_RETIRABLE_HINTS = {
    AssetStatus.ASSIGNED: "Return it first.",
    AssetStatus.UNDER_MAINTENANCE: "Finish the repair first.",
}


def _lock(db: Session, asset: Asset) -> Asset:
    """Row-lock the asset and reload its current values, so two people editing or
    retiring at the same moment cannot both act on an out-of-date status."""
    stmt = (
        select(Asset)
        .where(Asset.id == asset.id)
        .with_for_update(of=Asset)  # lock only the asset row, not the joined user / category rows
        .execution_options(populate_existing=True)
    )
    return db.scalars(stmt).one()


def _ensure_not_retired(asset: Asset) -> None:
    if asset.status == AssetStatus.RETIRED:
        raise AppError(409, "asset_retired", f"{asset.asset_code} is retired. A retired asset cannot be changed.")


def _commit(db: Session) -> None:
    """Commit; a serial number saved by someone else at the same moment becomes the normal 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if SERIAL_INDEX in str(exc.orig):
            raise serial_taken_error() from None
        raise
    except Exception:
        db.rollback()
        raise


# field: (required, max length, error code, label)
_EDIT_TEXT_RULES = {
    "name": (True, NAME_MAX_LENGTH, "invalid_asset_name", "asset name"),
    "serial_number": (True, SERIAL_MAX_LENGTH, "invalid_serial_number", "serial number"),
    "model": (True, MODEL_MAX_LENGTH, "invalid_model", "model"),
    "brand": (False, BRAND_MAX_LENGTH, "invalid_brand", "brand"),
    "location": (False, LOCATION_MAX_LENGTH, "invalid_location", "location"),
}


def _clean_edit(db: Session, field: str, value: Any, asset: Asset) -> Any:
    """Check and tidy one edited value (the same rules as when the asset was created).
    The warranty / purchase date rule (B61) is checked on the final values afterwards."""
    if field in MANUAL_ONLY_FIELDS:
        if asset.purchase_line_id is not None:
            raise AppError(
                422, "validation_error",
                "Category, purchase date and cost come from the purchase and cannot be changed on a received asset.",
                {"field": field},
            )
        if field == "category_id":
            if value is None:
                raise AppError(422, "validation_error", "Please choose a category.", {"field": field})
            return value if value == asset.category_id else _manual_category(db, value).id
        if field == "purchase_date":
            return _manual_purchase_date(value)
        return value  # cost: format already checked (AssetCost)
    if field == "warranty_expiry":
        return value
    required, max_length, code, label = _EDIT_TEXT_RULES[field]
    return _text(value, required=required, max_length=max_length, code=code, label=label)


def update_asset(
    db: Session,
    *,
    actor: User,
    asset: Asset,
    changes: dict[str, Any],
    context: AuditContext | None = None,
) -> Asset:
    """Change the editable details (A2). `changes` holds only the fields sent; null
    clears an optional field (brand, location, warranty) and is refused for a
    required one (name, model, serial number).

    Errors: 409 `asset_retired`; 409 `serial_number_taken`; 422 `invalid_*`.
    Nothing changed: nothing saved and no audit row (same as other records, B16)."""
    asset = _lock(db, asset)
    try:
        _ensure_not_retired(asset)
        new_values: dict[str, Any] = {}
        for field, value in changes.items():
            cleaned = _clean_edit(db, field, value, asset)
            if cleaned != getattr(asset, field):
                new_values[field] = cleaned
        final_warranty = new_values.get("warranty_expiry", asset.warranty_expiry)
        final_purchase = new_values.get("purchase_date", asset.purchase_date)
        if ("warranty_expiry" in new_values or "purchase_date" in new_values) and final_warranty and final_purchase \
                and final_warranty < final_purchase:
            raise AppError(
                422, "invalid_warranty_expiry",
                f"The warranty expiry cannot be before the purchase date ({final_purchase.isoformat()}).",
            )
        serial = new_values.get("serial_number")
        if serial is not None and serial.lower() != asset.serial_number.lower():
            clash = db.scalar(
                select(Asset.id).where(func.lower(Asset.serial_number) == serial.lower(), Asset.id != asset.id)
            )
            if clash is not None:
                raise serial_taken_error(serial)
    except Exception:
        db.rollback()  # releases the row lock; nothing was changed
        raise
    if not new_values:
        db.rollback()
        return asset

    before = {field: getattr(asset, field) for field in new_values}
    after = dict(new_values)
    if "category_id" in new_values:  # names too, so the history reads "Laptops -> Desktops" (I4)
        before["category"] = asset.category.name
        after["category"] = db.get(AssetCategory, new_values["category_id"]).name
    for field, value in new_values.items():
        setattr(asset, field, value)
    try:
        audit.record(
            db, actor=actor, action=AuditAction.ASSET_UPDATED, entity=asset,
            before=before, after=after, context=context,
        )
    except Exception:
        db.rollback()
        raise
    _commit(db)
    db.refresh(asset)
    return asset


def retire_asset(
    db: Session,
    *,
    actor: User,
    asset: Asset,
    reason: str | None,
    context: AuditContext | None = None,
) -> Asset:
    """Retire the asset (AST-07, A3): only from Available or Damaged, with a required
    reason. Stores who, when and why on the asset (F2) and writes asset.retired, all in
    one transaction. Cannot be undone.

    Errors: 409 `asset_retired` (already retired); 409 `asset_not_retirable` (Assigned
    or Under Maintenance, `details.status`); 422 `invalid_retire_reason`."""
    asset = _lock(db, asset)
    try:
        _ensure_not_retired(asset)
        if asset.status not in RETIRABLE_STATUSES:
            label = _STATUS_LABELS.get(asset.status, asset.status)
            hint = _NOT_RETIRABLE_HINTS.get(asset.status, "")
            raise AppError(
                409,
                "asset_not_retirable",
                f"{asset.asset_code} is {label}. Only Available or Damaged assets can be retired. {hint}".strip(),
                {"status": asset.status},
            )
        clean_reason = _text(
            reason, required=True, max_length=RETIRE_REASON_MAX_LENGTH,
            code="invalid_retire_reason", label="reason for retiring",
        )
    except Exception:
        db.rollback()  # releases the row lock; nothing was changed
        raise

    before = {"status": asset.status}
    asset.status = AssetStatus.RETIRED
    asset.retired_by_user_id = actor.id
    asset.retired_at = func.now()  # database time, like the audit row
    asset.retire_reason = clean_reason
    try:
        audit.record(
            db, actor=actor, action=AuditAction.ASSET_RETIRED, entity=asset,
            before=before, after={"status": AssetStatus.RETIRED, "reason": clean_reason}, context=context,
        )
    except Exception:
        db.rollback()
        raise
    _commit(db)
    db.refresh(asset)
    return asset
