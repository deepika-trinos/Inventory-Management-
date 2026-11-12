"""The employees table (Slice 1.3 minimal; completed in Slice 2.2, EMP-01 to EMP-03).

- employee_code ("employee ID" in the PRD) is unique ignoring upper/lower case.
- work_email is optional, stored in lower case (B5) and unique ignoring case.
- department is typed in (decision B23); designation and phone are optional.
- Never deleted, only deactivated (BR-12). EMP-05 (no new assignments to
  inactive employees) is enforced in Phase 5.
- A user login MAY be linked to one employee (users.employee_id, unique). From
  Slice 2.2 every Employee-role user must be linked (order fix b, R3).
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class EmployeeStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"

    ALL = (ACTIVE, INACTIVE)


EMPLOYEE_STATUSES = EmployeeStatus.ALL  # kept for older imports

CODE_MAX_LENGTH = 30
NAME_MAX_LENGTH = 150
DEPARTMENT_MAX_LENGTH = 100
DESIGNATION_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 255
PHONE_MAX_LENGTH = 30


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(CODE_MAX_LENGTH), nullable=False)
    full_name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), nullable=False)
    department: Mapped[str | None] = mapped_column(String(DEPARTMENT_MAX_LENGTH))
    designation: Mapped[str | None] = mapped_column(String(DESIGNATION_MAX_LENGTH))
    work_email: Mapped[str | None] = mapped_column(String(EMAIL_MAX_LENGTH))
    phone: Mapped[str | None] = mapped_column(String(PHONE_MAX_LENGTH))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EmployeeStatus.ACTIVE, server_default=EmployeeStatus.ACTIVE
    )

    # The login linked to this employee, if any (at most one: users.employee_id is unique).
    user: Mapped["User | None"] = relationship(back_populates="employee", uselist=False, lazy="selectin")

    @property
    def is_active(self) -> bool:
        return self.status == EmployeeStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<Employee {self.employee_code}>"


# Case-insensitive uniqueness and search indexes (migration 0005).
Index("uq_employees_employee_code_lower", func.lower(Employee.employee_code), unique=True)
Index("uq_employees_work_email_lower", func.lower(Employee.work_email), unique=True)
Index("ix_employees_full_name_lower", func.lower(Employee.full_name))
Index("ix_employees_department_lower", func.lower(Employee.department))
