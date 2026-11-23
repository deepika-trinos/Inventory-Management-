"""Request and response shapes for stock items (Slice 2.4, INV-01; Slice 4.3: the
low-stock flag and the movement history, INV-02, INV-05, INV-06).

quantity_on_hand is in the RESPONSE only (read-only). The request models
forbid unknown fields, so sending quantity_on_hand is a validation error:
the balance only changes through stock movements (Slices 3.3, 4.4, 4.5).
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.inventory.models import NAME_MAX_LENGTH

UnitField = Literal["pieces", "boxes", "packs", "pairs", "sets", "rolls", "metres"]
StockItemStatusField = Literal["active", "inactive"]
MAX_THRESHOLD = 1_000_000


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tracking_type: str
    status: str


class StockItemRead(BaseModel):
    """A stock item as shown by the API. All times are UTC (ISO 8601 with offset)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: CategorySummary
    unit_of_measure: UnitField
    reorder_threshold: int
    quantity_on_hand: int = Field(description="Read-only. Changes only through stock movements.")
    low_stock: bool = Field(
        description="Active item with quantity on hand at or below its reorder threshold (INV-06, B37, G1)."
    )
    status: StockItemStatusField
    created_at: datetime
    updated_at: datetime


class StockItemPage(BaseModel):
    """One page of stock items: the shared paged-list format."""

    items: list[StockItemRead]
    total: int
    page: int
    page_size: int


class MovementUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class MovementEmployee(BaseModel):
    """The employee an issue went to (Slice 4.4, A4)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str


class MovementReference(BaseModel):
    """What caused the movement. Receipts: their purchase (C3). Later slices add others."""

    purchase_id: int
    purchase_number: str
    purchase_line_id: int


class StockMovementRead(BaseModel):
    """One line of a stock item's movement history (INV-05, BR-09)."""

    id: int
    movement_type: Literal["receipt", "issue", "adjustment_in", "adjustment_out", "opening"]
    direction: Literal["in", "out"]
    quantity: int = Field(description="Always above 0; `direction` says whether stock went in or out.")
    change: int = Field(description="Signed change to the balance: +quantity in, -quantity out.")
    balance_after: int = Field(description="The item's balance right after this movement (C4).")
    movement_date: date = Field(description="The business date, e.g. the received date (C2).")
    created_at: datetime = Field(description="When it was saved (UTC).")
    created_by: MovementUser
    reason: str | None = Field(description="Required for issues and adjustments (Slice 4.4); empty for receipts.")
    reference: MovementReference | None
    issued_to: MovementEmployee | None = Field(default=None, description="Issues only: the employee who received it (A4).")


MAX_CHANGE_QUANTITY = 1_000_000  # technical limit, like the reorder threshold (B37)


class StockIssue(BaseModel):
    """Issue stock (Slice 4.4, INV-04; owner's answers A4, A4-5a). Reason required;
    employee optional (active employees only); date defaults to today (company
    timezone), may be earlier, never in the future."""

    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(gt=0, le=MAX_CHANGE_QUANTITY, description="Whole number above 0.")
    reason: str | None = Field(default=None, max_length=5000, description="Required, up to 500 characters.")
    employee_id: int | None = Field(default=None, ge=1, description="Optional: the employee who received it.")
    movement_date: date | None = Field(default=None, description="Default: today. Earlier allowed, future refused.")


class StockAdjust(BaseModel):
    """Adjust stock (Slice 4.4; owner's answers A5, A4-5a): add or remove N with a reason."""

    model_config = ConfigDict(extra="forbid")

    direction: Literal["add", "remove"]
    quantity: int = Field(gt=0, le=MAX_CHANGE_QUANTITY, description="Whole number above 0.")
    reason: str | None = Field(default=None, max_length=5000, description="Required, up to 500 characters.")
    movement_date: date | None = Field(default=None, description="Default: today. Earlier allowed, future refused.")


class StockMovementPage(BaseModel):
    items: list[StockMovementRead]
    total: int
    page: int
    page_size: int


class StockChangeResult(BaseModel):
    """What an issue or adjustment returns: the item with its new balance, and the movement."""

    item: StockItemRead
    movement: StockMovementRead


# ---- Requests (quantity_on_hand is deliberately NOT accepted) ---------------------------
class StockItemCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"name": "USB mouse", "category_id": 2, "unit_of_measure": "pieces", "reorder_threshold": 10}]
        },
    )

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH, description="Unique within its category, any case.")
    category_id: int = Field(description="An ACTIVE category tracked by quantity ('bulk').")
    unit_of_measure: UnitField
    reorder_threshold: int = Field(ge=0, le=MAX_THRESHOLD, description="Low stock at or below this quantity.")


class StockItemUpdate(BaseModel):
    """Send only the fields you want to change. Status has its own actions."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    category_id: int | None = None
    unit_of_measure: UnitField | None = None
    reorder_threshold: int | None = Field(default=None, ge=0, le=MAX_THRESHOLD)
