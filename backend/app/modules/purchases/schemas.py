"""Request and response shapes for purchases (Slice 3.1, PUR-01 to PUR-04).

Money (P2): INR, 2 decimal places. Amounts are sent as JSON strings ("1250.00")
so no rounding happens on the way; requests accept a number or a string.
Totals (line_total, total_amount) are calculated by the server: requests cannot
send them (unknown fields are refused).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.purchases.models import DESCRIPTION_MAX_LENGTH, NOTES_MAX_LENGTH, REFERENCE_MAX_LENGTH

PurchaseStatusField = Literal["draft", "received", "cancelled"]
LineTypeField = Literal["serialized", "bulk"]

# Technical limits (B44), not from the PRD.
MAX_LINES = 100
MAX_QUANTITY = 100_000
UnitCost = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, description="INR, 2 decimals, 0 allowed.")]


# ---- Responses ----------------------------------------------------------------------
class VendorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class StockItemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    unit_of_measure: str
    status: str


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tracking_type: str
    status: str


class PurchaseLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_type: LineTypeField
    stock_item: StockItemSummary | None = Field(description="Set on 'bulk' lines.")
    category: CategorySummary | None = Field(description="Set on 'serialized' lines.")
    description: str | None = Field(description="Set on 'serialized' lines.")
    quantity: int
    unit_cost: Decimal
    line_total: Decimal = Field(description="quantity x unit_cost (calculated).")
    received_quantity: int | None = Field(description="Empty until the purchase is received (3.2 / 3.3).")


class PurchaseSummary(BaseModel):
    """A purchase in the list (without its lines)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_number: str
    vendor: VendorSummary
    reference_number: str
    purchase_date: date
    received_date: date | None
    status: PurchaseStatusField
    line_count: int
    total_amount: Decimal = Field(description="Sum of the line totals (calculated).")
    created_at: datetime
    updated_at: datetime


class PurchaseRead(PurchaseSummary):
    """One purchase with its lines. All times are UTC (ISO 8601 with offset)."""

    notes: str | None
    created_by: UserSummary
    lines: list[PurchaseLineRead]


class PurchasePage(BaseModel):
    """One page of purchases: the shared paged-list format."""

    items: list[PurchaseSummary]
    total: int
    page: int
    page_size: int


# ---- Requests -------------------------------------------------------------------------
class PurchaseLineIn(BaseModel):
    """One line. 'bulk': send stock_item_id. 'serialized': send category_id and description."""

    model_config = ConfigDict(extra="forbid")

    line_type: LineTypeField
    stock_item_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    quantity: int = Field(ge=1, le=MAX_QUANTITY, description="Whole number, 1 or more.")
    unit_cost: UnitCost


class PurchaseCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "vendor_id": 1,
                    "reference_number": "INV-2026-0042",
                    "purchase_date": "2026-11-12",
                    "notes": "Q4 laptop refresh",
                    "lines": [
                        {
                            "line_type": "serialized",
                            "category_id": 1,
                            "description": "Laptops: Dell Latitude 5440",
                            "quantity": 3,
                            "unit_cost": "85000.00",
                        },
                        {"line_type": "bulk", "stock_item_id": 1, "quantity": 10, "unit_cost": "450.00"},
                    ],
                }
            ]
        },
    )

    vendor_id: int = Field(description="An ACTIVE vendor.")
    reference_number: str = Field(
        min_length=1, max_length=REFERENCE_MAX_LENGTH, description="Invoice / reference number. Unique per vendor."
    )
    purchase_date: date = Field(description="Not in the future (company timezone).")
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    lines: list[PurchaseLineIn] = Field(max_length=MAX_LINES, description="At least one line.")


class PurchaseUpdate(BaseModel):
    """Send only what changes. `lines`, when sent, REPLACES all lines of the draft.
    `notes: null` clears the notes. Only a draft can be edited."""

    model_config = ConfigDict(extra="forbid")

    vendor_id: int | None = None
    reference_number: str | None = Field(default=None, min_length=1, max_length=REFERENCE_MAX_LENGTH)
    purchase_date: date | None = None
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    lines: list[PurchaseLineIn] | None = Field(default=None, max_length=MAX_LINES)
