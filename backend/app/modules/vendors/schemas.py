"""Request and response shapes for vendors (Slice 2.3, VEN-01 to VEN-03)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.vendors.models import (
    ADDRESS_MAX_LENGTH,
    CONTACT_PERSON_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    NAME_MAX_LENGTH,
    PHONE_MAX_LENGTH,
)

VendorStatusField = Literal["active", "inactive"]


class VendorRead(BaseModel):
    """A vendor as shown by the API. All times are UTC (ISO 8601 with offset)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    status: VendorStatusField
    created_at: datetime
    updated_at: datetime


class VendorPage(BaseModel):
    """One page of vendors: the shared paged-list format."""

    items: list[VendorRead]
    total: int
    page: int
    page_size: int


# ---- Requests ------------------------------------------------------------------------
class VendorCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Acme IT Supplies",
                    "contact_person": "Priya Nair",
                    "email": "sales@acme.example.com",
                    "phone": "+91 80 1234 5678",
                    "address": "12 MG Road, Bengaluru 560001",
                }
            ]
        }
    )

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH, description="Unique, ignoring upper/lower case.")
    contact_person: str | None = Field(default=None, max_length=CONTACT_PERSON_MAX_LENGTH)
    email: str | None = Field(default=None, max_length=EMAIL_MAX_LENGTH, description="Stored in lower case.")
    phone: str | None = Field(default=None, max_length=PHONE_MAX_LENGTH)
    address: str | None = Field(default=None, max_length=ADDRESS_MAX_LENGTH)


class VendorUpdate(BaseModel):
    """Send only the fields you want to change. null clears an optional field.
    Status has its own activate/deactivate actions."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    contact_person: str | None = Field(default=None, max_length=CONTACT_PERSON_MAX_LENGTH)
    email: str | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    phone: str | None = Field(default=None, max_length=PHONE_MAX_LENGTH)
    address: str | None = Field(default=None, max_length=ADDRESS_MAX_LENGTH)
