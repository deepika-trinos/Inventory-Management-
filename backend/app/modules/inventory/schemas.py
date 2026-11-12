"""Request and response shapes for stock items (Slice 2.4, INV-01).

quantity_on_hand is in the RESPONSE only (read-only). The request models
forbid unknown fields, so sending quantity_on_hand is a validation error:
the balance only changes through stock movements (Slices 3.3, 4.4, 4.5).
"""

from datetime import datetime
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
    status: StockItemStatusField
    created_at: datetime
    updated_at: datetime


class StockItemPage(BaseModel):
    """One page of stock items: the shared paged-list format."""

    items: list[StockItemRead]
    total: int
    page: int
    page_size: int


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
