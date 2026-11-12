"""Request and response shapes for asset categories (Slice 2.1)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.categories.models import DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH

TrackingTypeField = Literal["serialized", "bulk"]
CategoryStatusField = Literal["active", "inactive"]


class CategoryRead(BaseModel):
    """A category as shown by the API. All times are UTC (ISO 8601 with offset)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    tracking_type: TrackingTypeField
    status: CategoryStatusField
    created_at: datetime
    updated_at: datetime


class CategoryPage(BaseModel):
    """One page of categories: the shared paged-list format."""

    items: list[CategoryRead]
    total: int
    page: int
    page_size: int


# ---- Requests ------------------------------------------------------------------------
class CategoryCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Laptops", "description": "Company laptops", "tracking_type": "serialized"},
                {"name": "Mice", "tracking_type": "bulk"},
            ]
        }
    )

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH, description="Unique, ignoring upper/lower case.")
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    tracking_type: TrackingTypeField = Field(
        description='"serialized" = tracked one by one; "bulk" = tracked by quantity.'
    )


class CategoryUpdate(BaseModel):
    """Send only the fields you want to change. description: null clears it.
    Status has its own activate/deactivate actions."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    tracking_type: TrackingTypeField | None = None
