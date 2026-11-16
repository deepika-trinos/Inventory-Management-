"""Assets: read one, and the shared checks used when assets are created
(Slice 3.2: receiving a purchase; Slice 4.5 will reuse them for manual entry).

RULES (AST-01, AST-02, AST-06, BR-01, P5)
- The asset ID (AST-000001, ...) is made by the database sequence: never typed.
- Serial number and model are required; brand, warranty expiry and location
  (typed text, Q1) are optional. Warranty expiry, when given, is not before the
  purchase date (B61). Text is trimmed; empty optional text is stored as empty (NULL).
- Serial numbers are unique across ALL assets ignoring case. The service checks
  first to give a clear error; the unique index uq_assets_serial_number_lower is
  the final guard when two receipts are saved at the same moment.
- Assets are never deleted (BR-12). There is no delete function and no DELETE endpoint.
"""

from collections.abc import Iterable
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.assets.models import (
    ASSET_CODE_PREFIX,
    BRAND_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    MODEL_MAX_LENGTH,
    NAME_MAX_LENGTH,
    SERIAL_MAX_LENGTH,
    Asset,
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
