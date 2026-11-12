"""Request and response shapes for employees (Slice 2.2, EMP-01 to EMP-03)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.employees.models import (
    CODE_MAX_LENGTH,
    DEPARTMENT_MAX_LENGTH,
    DESIGNATION_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    NAME_MAX_LENGTH,
    PHONE_MAX_LENGTH,
)

EmployeeStatusField = Literal["active", "inactive"]


class LinkedLogin(BaseModel):
    """The login linked to an employee (no password data, ever)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool


class EmployeeRead(BaseModel):
    """An employee as shown by the API. All times are UTC (ISO 8601 with offset)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    department: str | None = None
    designation: str | None = None
    work_email: str | None = None
    phone: str | None = None
    status: EmployeeStatusField
    user: LinkedLogin | None = Field(default=None, description="The linked login, if any.")
    created_at: datetime
    updated_at: datetime


class EmployeePage(BaseModel):
    """One page of employees: the shared paged-list format."""

    items: list[EmployeeRead]
    total: int
    page: int
    page_size: int


# ---- Requests ------------------------------------------------------------------------
class EmployeeCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "employee_code": "EMP-001",
                    "full_name": "Asha Kumar",
                    "department": "Finance",
                    "designation": "Accountant",
                    "work_email": "asha.kumar@example.com",
                    "phone": "+91 98765 43210",
                }
            ]
        }
    )

    employee_code: str = Field(
        min_length=1, max_length=CODE_MAX_LENGTH, description="Employee ID. Unique, ignoring upper/lower case."
    )
    full_name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    department: str | None = Field(default=None, max_length=DEPARTMENT_MAX_LENGTH)
    designation: str | None = Field(default=None, max_length=DESIGNATION_MAX_LENGTH)
    work_email: str | None = Field(
        default=None, max_length=EMAIL_MAX_LENGTH, description="Stored in lower case. Unique when given."
    )
    phone: str | None = Field(default=None, max_length=PHONE_MAX_LENGTH)


class EmployeeUpdate(BaseModel):
    """Send only the fields you want to change. null clears an optional field.
    Status has its own activate/deactivate actions."""

    employee_code: str | None = Field(default=None, min_length=1, max_length=CODE_MAX_LENGTH)
    full_name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    department: str | None = Field(default=None, max_length=DEPARTMENT_MAX_LENGTH)
    designation: str | None = Field(default=None, max_length=DESIGNATION_MAX_LENGTH)
    work_email: str | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    phone: str | None = Field(default=None, max_length=PHONE_MAX_LENGTH)
