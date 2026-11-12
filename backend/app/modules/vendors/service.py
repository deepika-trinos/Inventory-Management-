"""Vendors: list, get, create, edit, activate/deactivate (Slice 2.3, VEN-01 to VEN-03, VEN-05).

Used by the /vendors endpoints (Admin and IT Manager) and, from Slice 3.1, by
purchases (see ensure_vendor_active). Slice 3.4 adds the purchase history.

Every change writes an audit row in the SAME transaction (BR-13, B11).

RULES
- Name is required and unique ignoring upper/lower case, active or inactive (B30).
- Contact person, email, phone and address are optional ("where available",
  B31). Email is stored in lower case (B5), checked for format, and may repeat.
  Phone uses the same check as employees (B22).
- BR-12 / VEN-05: vendors are NEVER deleted, only deactivated. There is no
  delete function here and no DELETE endpoint.
- A deactivated vendor stays readable, but purchases may only be created from
  an ACTIVE vendor: ensure_vendor_active() (first used in Slice 3.1).
"""

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.core.text import clean_phone, optional_text, required_text
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.users.models import User
from app.modules.users.service import validate_email
from app.modules.vendors.models import Vendor, VendorStatus

# What the audit log records about a vendor.
_AUDIT_FIELDS = ["name", "contact_person", "email", "phone", "address", "status"]
_FIELDS = ("name", "contact_person", "email", "phone", "address")

# Fields the vendor list can be sorted by.
_SORTABLE = {
    "name": func.lower(Vendor.name),
    "contact_person": func.lower(Vendor.contact_person),
    "email": Vendor.email,
    "status": Vendor.status,
    "created_at": Vendor.created_at,
    "updated_at": Vendor.updated_at,
}

# Name of the unique index on lower(name) (migration 0006).
_NAME_INDEX = "uq_vendors_name_lower"


# ---- Small helpers ------------------------------------------------------------------
def _name_taken_error() -> AppError:
    return AppError(409, "vendor_name_taken", "A vendor with this name already exists.")


def _clean(field: str, value: Any) -> Any:
    if field == "name":
        return required_text(value, "invalid_name", "Please enter the vendor's name.")
    if field == "email":
        value = optional_text(value)
        return validate_email(value) if value else None  # lower case (B5)
    if field == "phone":
        return clean_phone(value)
    return optional_text(value)  # contact_person, address


def get_vendor(db: Session, vendor_id: int) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise AppError(404, "vendor_not_found", "Vendor not found.")
    return vendor


def get_vendor_by_name(db: Session, name: str) -> Vendor | None:
    return db.scalar(select(Vendor).where(func.lower(Vendor.name) == name.strip().lower()))


def _ensure_name_free(db: Session, name: str, *, except_id: int | None = None) -> None:
    existing = get_vendor_by_name(db, name)
    if existing is not None and existing.id != except_id:
        raise _name_taken_error()


def ensure_vendor_active(db: Session, vendor_id: int) -> Vendor:
    """Return the vendor if a NEW purchase may use it; otherwise raise.

    A deactivated vendor stays readable (list, get one, later its purchase
    history) but cannot be used for new purchases. Not called anywhere yet:
    Slice 3.1 (draft purchases) calls it when a purchase is created or its
    vendor is changed.
    """
    vendor = get_vendor(db, vendor_id)
    if not vendor.is_active:
        raise AppError(
            409,
            "vendor_inactive",
            f'Vendor "{vendor.name}" is deactivated and cannot be used for new purchases.',
        )
    return vendor


def _save(
    db: Session,
    *,
    actor: User | None,
    action: str,
    vendor: Vendor,
    before: dict[str, Any] | None,
    context: AuditContext | None,
) -> Vendor:
    """Write the audit row and commit the change together; undo both on any error."""
    try:
        audit.record(
            db,
            actor=actor,
            action=action,
            entity=vendor,
            before=before,
            after=audit.snapshot(vendor, _AUDIT_FIELDS),
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
    db.refresh(vendor)
    return vendor


# ---- Reading ----------------------------------------------------------------------
def list_vendors(
    db: Session,
    params: PageParams,
    *,
    search: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Paged vendor list (VEN-03). `search` matches part of the name, contact
    person, email or phone, ignoring case."""
    stmt: Select = select(Vendor)
    if search and search.strip():
        term = search.strip().lower()
        stmt = stmt.where(
            or_(
                func.lower(Vendor.name).contains(term, autoescape=True),
                func.lower(Vendor.contact_person).contains(term, autoescape=True),
                Vendor.email.contains(term, autoescape=True),  # already lower case
                func.lower(Vendor.phone).contains(term, autoescape=True),
            )
        )
    if status:
        stmt = stmt.where(Vendor.status == status)
    return paginate(db, stmt, params, sortable=_SORTABLE, default_sort="name")


# ---- Changing ---------------------------------------------------------------------
def create_vendor(
    db: Session,
    *,
    data: dict[str, Any],
    actor: User | None = None,
    context: AuditContext | None = None,
) -> Vendor:
    """Create an active vendor (audit: vendor.created)."""
    values = {field: _clean(field, data.get(field)) if data.get(field) is not None or field == "name" else None
              for field in _FIELDS}
    _ensure_name_free(db, values["name"])
    vendor = Vendor(**values, status=VendorStatus.ACTIVE)
    db.add(vendor)
    return _save(db, actor=actor, action=AuditAction.VENDOR_CREATED, vendor=vendor, before=None, context=context)


def update_vendor(
    db: Session,
    *,
    actor: User | None,
    vendor: Vendor,
    changes: dict[str, Any],
    context: AuditContext | None = None,
) -> Vendor:
    """Change any detail except status (audit: vendor.updated).

    `changes` holds only the fields actually sent; null clears an optional
    field (the name cannot be cleared). Works on inactive vendors too.
    """
    before = audit.snapshot(vendor, _AUDIT_FIELDS)
    new_values: dict[str, Any] = {}
    for field, value in changes.items():
        if field not in _FIELDS or (field == "name" and value is None):
            continue  # unknown field, or "null" for the required name: leave as it is
        cleaned = _clean(field, value)
        if cleaned != getattr(vendor, field):
            new_values[field] = cleaned

    if not new_values:
        return vendor  # nothing to save or record
    name = new_values.get("name")
    if name is not None and name.lower() != vendor.name.lower():
        _ensure_name_free(db, name, except_id=vendor.id)
    for field, value in new_values.items():
        setattr(vendor, field, value)
    return _save(db, actor=actor, action=AuditAction.VENDOR_UPDATED, vendor=vendor, before=before, context=context)


def set_active(
    db: Session,
    *,
    actor: User | None,
    vendor: Vendor,
    active: bool,
    context: AuditContext | None = None,
) -> Vendor:
    """Activate or deactivate (audit: vendor.activated / vendor.deactivated).

    Never deletes anything (BR-12, VEN-05). Existing purchases keep the vendor.
    """
    new_status = VendorStatus.ACTIVE if active else VendorStatus.INACTIVE
    if vendor.status == new_status:
        return vendor  # already in that state
    before = audit.snapshot(vendor, _AUDIT_FIELDS)
    vendor.status = new_status
    action = AuditAction.VENDOR_ACTIVATED if active else AuditAction.VENDOR_DEACTIVATED
    return _save(db, actor=actor, action=action, vendor=vendor, before=before, context=context)
