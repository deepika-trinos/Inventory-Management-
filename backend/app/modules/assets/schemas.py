"""Response shapes for assets (Slice 3.2; asset register Slice 4.1).

Reading only: one asset (with where it came from), the asset register (list,
search, filters) and an asset's history. Editing and retiring come in Slice 4.2;
manual entry in Slice 4.5.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

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
