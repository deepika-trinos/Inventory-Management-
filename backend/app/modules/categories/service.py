"""Asset categories: list, get, create, edit, activate/deactivate (Slice 2.1, AST-02).

Used by the /categories endpoints (Admin and IT Manager) and, from Slice 2.4
onward, by the stock-item and asset code (see ensure_category_selectable).

Every change writes an audit row in the SAME transaction (BR-13, decision B11),
so a change is never saved without its audit row, or the other way round.

RULES
- Name is unique ignoring upper/lower case (active and inactive categories alike).
- BR-12 (decisions.md gap 2): categories are NEVER deleted, only deactivated.
  There is deliberately no delete function here and no DELETE endpoint.
- A deactivated category stays readable, but cannot be chosen for new records
  (ensure_category_selectable; enforced from Slice 2.4 onward).
- tracking_type cannot change once any item or asset uses the category
  (_category_in_use; starts to apply from Slice 2.4 / 3.2 onward).
"""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.categories.models import AssetCategory, CategoryStatus
from app.modules.users.models import User

# What the audit log records about a category.
_AUDIT_FIELDS = ["name", "description", "tracking_type", "status"]

# Fields the category list can be sorted by.
_SORTABLE = {
    "name": func.lower(AssetCategory.name),
    "tracking_type": AssetCategory.tracking_type,
    "status": AssetCategory.status,
    "created_at": AssetCategory.created_at,
    "updated_at": AssetCategory.updated_at,
}

# Name of the unique index on lower(name) (migration 0004).
_NAME_INDEX = "uq_asset_categories_name_lower"


# ---- Small helpers ------------------------------------------------------------------
def _clean_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise AppError(422, "invalid_name", "Please enter a category name.")
    return name


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    return description.strip() or None


def _name_taken_error() -> AppError:
    return AppError(409, "category_name_taken", "A category with this name already exists.")


def get_category_by_name(db: Session, name: str) -> AssetCategory | None:
    return db.scalar(select(AssetCategory).where(func.lower(AssetCategory.name) == name.strip().lower()))


def get_category(db: Session, category_id: int) -> AssetCategory:
    category = db.get(AssetCategory, category_id)
    if category is None:
        raise AppError(404, "category_not_found", "Category not found.")
    return category


def _ensure_name_free(db: Session, name: str, *, except_id: int | None = None) -> None:
    existing = get_category_by_name(db, name)
    if existing is not None and existing.id != except_id:
        raise _name_taken_error()


def _category_in_use(db: Session, category: AssetCategory) -> bool:
    """Is any stock item or asset using this category?

    - Slice 2.4: stock items count (any status: an inactive item still uses it).
    - Slice 3.2 (serialized assets): ADD a check on assets.category_id here.
    """
    from app.modules.inventory.models import StockItem  # here, to avoid a circular import

    return db.scalar(select(StockItem.id).where(StockItem.category_id == category.id).limit(1)) is not None


def ensure_category_selectable(db: Session, category_id: int) -> AssetCategory:
    """Return the category if it can be chosen for a NEW record; otherwise raise.

    A deactivated category stays readable (list / get one) but must not be
    picked for new stock items or assets (BR-12). Not called anywhere yet:
    Slice 2.4 (stock items) and Slice 3.1/3.2 (purchases, assets) call it.
    """
    category = get_category(db, category_id)
    if not category.is_active:
        raise AppError(
            409,
            "category_inactive",
            f'Category "{category.name}" is deactivated and cannot be used for new records.',
        )
    return category


def _save(
    db: Session,
    *,
    actor: User | None,
    action: str,
    category: AssetCategory,
    before: dict[str, Any] | None,
    context: AuditContext | None,
) -> AssetCategory:
    """Write the audit row and commit the change together; undo both on any error."""
    try:
        audit.record(
            db,
            actor=actor,
            action=action,
            entity=category,
            before=before,
            after=audit.snapshot(category, _AUDIT_FIELDS),
            context=context,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Two people saving the same name at the same moment: the unique index wins.
        if _NAME_INDEX in str(exc.orig):
            raise _name_taken_error() from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(category)
    return category


# ---- Reading ----------------------------------------------------------------------
def list_categories(
    db: Session,
    params: PageParams,
    *,
    search: str | None = None,
    tracking_type: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Paged category list. `search` matches part of the name (any case)."""
    stmt: Select = select(AssetCategory)
    if search and search.strip():
        stmt = stmt.where(func.lower(AssetCategory.name).contains(search.strip().lower(), autoescape=True))
    if tracking_type:
        stmt = stmt.where(AssetCategory.tracking_type == tracking_type)
    if status:
        stmt = stmt.where(AssetCategory.status == status)
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="name")


# ---- Changing ---------------------------------------------------------------------
def create_category(
    db: Session,
    *,
    name: str,
    tracking_type: str,
    description: str | None = None,
    actor: User | None = None,
    context: AuditContext | None = None,
) -> AssetCategory:
    """Create an active category (audit: category.created)."""
    name = _clean_name(name)
    _ensure_name_free(db, name)
    category = AssetCategory(
        name=name,
        description=_clean_description(description),
        tracking_type=tracking_type,
        status=CategoryStatus.ACTIVE,
    )
    db.add(category)
    return _save(db, actor=actor, action=AuditAction.CATEGORY_CREATED, category=category, before=None, context=context)


def update_category(
    db: Session,
    *,
    actor: User | None,
    category: AssetCategory,
    changes: dict[str, Any],
    context: AuditContext | None = None,
) -> AssetCategory:
    """Change name, description and/or tracking type (audit: category.updated).

    `changes` holds only the fields actually sent. description=None clears it.
    Status has its own actions (set_active). Works on inactive categories too.
    """
    before = audit.snapshot(category, _AUDIT_FIELDS)
    changed = False

    if changes.get("name") is not None:
        name = _clean_name(changes["name"])
        if name != category.name:
            if name.lower() != category.name.lower():
                _ensure_name_free(db, name, except_id=category.id)
            category.name = name
            changed = True

    if "description" in changes:
        description = _clean_description(changes["description"])
        if description != category.description:
            category.description = description
            changed = True

    if changes.get("tracking_type") is not None and changes["tracking_type"] != category.tracking_type:
        # GUARD: once a stock item or asset uses this category, switching between
        # one-by-one and by-quantity would leave those records in the wrong model
        # (PRD 9.2). It only starts to apply from Slice 2.4 / 3.2 (see _category_in_use).
        if _category_in_use(db, category):
            raise AppError(
                409,
                "tracking_type_locked",
                "The tracking type cannot be changed because items or assets already use this category.",
            )
        category.tracking_type = changes["tracking_type"]
        changed = True

    if not changed:
        return category  # nothing to save or record
    return _save(db, actor=actor, action=AuditAction.CATEGORY_UPDATED, category=category, before=before, context=context)


def set_active(
    db: Session,
    *,
    actor: User | None,
    category: AssetCategory,
    active: bool,
    context: AuditContext | None = None,
) -> AssetCategory:
    """Activate or deactivate (audit: category.activated / category.deactivated).

    Never deletes anything (BR-12). Existing records keep their category.
    """
    new_status = CategoryStatus.ACTIVE if active else CategoryStatus.INACTIVE
    if category.status == new_status:
        return category  # already in that state
    before = audit.snapshot(category, _AUDIT_FIELDS)
    category.status = new_status
    action = AuditAction.CATEGORY_ACTIVATED if active else AuditAction.CATEGORY_DEACTIVATED
    return _save(db, actor=actor, action=action, category=category, before=before, context=context)
