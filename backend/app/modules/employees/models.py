"""Employee table (minimal for Slice 1.3).

Slice 2.2 adds department, designation, contact details and the employee
screens. For now a user account can optionally be linked to an employee
(order fix b in decisions.md).
"""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

EMPLOYEE_STATUSES = ("active", "inactive")


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    work_email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    def __repr__(self) -> str:
        return f"<Employee {self.employee_code}>"
