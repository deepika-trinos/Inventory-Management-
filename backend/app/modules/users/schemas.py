"""Response shapes for users.

These classes list EXACTLY which fields may leave the server. password_hash
is deliberately not a field here, so it can never appear in a response, even
if a route returns the full database object.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RoleNameField = Literal["Admin", "IT Manager", "Employee"]


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class EmployeeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    status: str


class UserRead(BaseModel):
    """A user as shown by the API. All times are UTC (ISO 8601 with offset)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    role: RoleRead
    employee: EmployeeSummary | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserPage(BaseModel):
    """One page of users: the shared paged-list format."""

    items: list[UserRead]
    total: int
    page: int
    page_size: int


# ---- Requests (what the Admin sends) -------------------------------------------------
class UserCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "it.manager@example.com", "password": "a-temporary-password", "role": "IT Manager"}
            ]
        }
    )

    email: str = Field(min_length=3, max_length=255, description="Login email (stored in lower case).")
    password: str = Field(
        min_length=1,
        max_length=256,
        description="Temporary password the Admin gives the user (minimum length: PASSWORD_MIN_LENGTH).",
    )
    role: RoleNameField
    employee_id: int | None = Field(
        default=None, description="Optional link to an employee record (one login per employee)."
    )


class UserUpdate(BaseModel):
    """Send only the fields you want to change. employee_id: null removes the link."""

    email: str | None = Field(default=None, min_length=3, max_length=255)
    employee_id: int | None = None


class RoleChange(BaseModel):
    role: RoleNameField
