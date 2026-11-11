"""Response shapes for users.

These classes list EXACTLY which fields may leave the server. password_hash
is deliberately not a field here, so it can never appear in a response, even
if a route returns the full database object.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
