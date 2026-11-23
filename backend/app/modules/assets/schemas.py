"""Response shapes for assets (Slice 3.2; asset register Slice 4.1).

Reading: one asset (with where it came from), the asset register (list, search,
filters) and an asset's history. Slice 4.2: editing the allowed details and
retiring. Manual entry comes in Slice 4.5.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AssetStatusField = Literal["available", "assigned", "under_maintenance", "damaged", "retired"]


class AssetCategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tracking_type: str
    status: str


class AssetUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class AssetPurchaseSummary(BaseModel):
    """Where the asset came from (empty for equipment entered by hand, Slice 4.5)."""

    purchase_id: int
    purchase_number: str
    purchase_line_id: int
    vendor_id: int
    vendor: str
    reference_number: str


class AssetLink(BaseModel):
    """An asset as listed under the purchase line it was received on."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    serial_number: str


class AssetRead(BaseModel):
    """One asset. All times are UTC (ISO 8601 with offset); dates are plain dates."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str = Field(description="AST-000001 ..., made by the system.")
    name: str
    category: AssetCategorySummary
    brand: str | None
    model: str
    serial_number: str
    status: AssetStatusField
    location: str | None
    warranty_expiry: date | None
    purchase_date: date | None
    cost: Decimal | None = Field(description="INR, 2 decimals (the purchase line's unit cost).")
    purchase: AssetPurchaseSummary | None = Field(default=None, description="Empty for equipment entered by hand.")
    created_by: AssetUserSummary
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None = Field(default=None, description="When it was retired (Slice 4.2).")
    retired_by: AssetUserSummary | None = Field(default=None, description="Who retired it.")
    retire_reason: str | None = Field(default=None, description="Why it was retired (required when retiring).")


# INR, 2 decimals, 0 allowed, NUMERIC(12,2): the same format as a purchase line's unit cost (P2, B44).
AssetCost = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, description="INR, 2 decimals, 0 allowed.")]


class AssetUpdate(BaseModel):
    """Edit an asset (Slice 4.2, owner's answer A2; Slice 4.5 for manual entries). Send only
    the fields to change; `null` clears brand, location, warranty expiry, and (manual
    entries) purchase date and cost. Category, purchase date and cost can be changed
    only on assets entered by hand (I4); on a received asset they are refused with 422
    `validation_error`. Any other field (status, asset ID, ...) is refused the same way:
    status changes only through actions (AST-07)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=1000)
    brand: str | None = Field(default=None, max_length=1000)
    model: str | None = Field(default=None, max_length=1000)
    serial_number: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=1000)
    warranty_expiry: date | None = None
    # Manual entries only (Slice 4.5, I4):
    category_id: int | None = Field(default=None, ge=1)
    purchase_date: date | None = None
    cost: AssetCost | None = None


class AssetCreate(BaseModel):
    """Enter equipment the company already owns, without a purchase (Slice 4.5, AST-01,
    Q4; owner's answer A7). The asset ID is made by the system; status is always
    Available; there is no purchase link or vendor."""

    model_config = ConfigDict(extra="forbid")

    category_id: int = Field(ge=1, description="An active one-by-one category.")
    serial_number: str | None = Field(default=None, max_length=1000, description="Required; unique ignoring case.")
    model: str | None = Field(default=None, max_length=1000, description="Required.")
    name: str | None = Field(default=None, max_length=1000, description="Required (no purchase line to name it after).")
    brand: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=1000)
    warranty_expiry: date | None = Field(default=None, description="Not before the purchase date (B61).")
    purchase_date: date | None = Field(default=None, description="Optional; not in the future.")
    cost: AssetCost | None = Field(default=None, description="Optional; INR, 2 decimals, 0 allowed.")


class AssetRetire(BaseModel):
    """Retire an asset (Slice 4.2, A3): the reason is required, up to 500 characters."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=5000, description="Why it is retired (required).")


class AssetListItem(BaseModel):
    """One row of the asset register (Slice 4.1)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    name: str
    category: AssetCategorySummary
    brand: str | None
    model: str
    serial_number: str
    status: AssetStatusField
    location: str | None
    warranty_expiry: date | None
    created_at: datetime


class AssetPage(BaseModel):
    items: list[AssetListItem]
    total: int
    page: int
    page_size: int


class AssetHistoryEntry(BaseModel):
    """One audit log row about the asset. `before` / `after` are what the audit log
    recorded (e.g. asset.created: the asset's details and its purchase number)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str = Field(description='e.g. "asset.created".')
    created_at: datetime
    actor: AssetUserSummary | None = Field(description="Empty for a system action.")
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class AssetHistoryPage(BaseModel):
    items: list[AssetHistoryEntry]
    total: int
    page: int
    page_size: int
