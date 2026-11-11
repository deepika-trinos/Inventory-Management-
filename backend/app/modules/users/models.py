"""Role and User tables.

- Every user has exactly ONE role (role_id is required) - PRD 4.1.
- A user MAY be linked to one employee record (employee_id is optional and
  unique: one login per employee at most) - decisions.md Q6 and order fix b.
- Email is unique ignoring upper/lower case: "Asha@X.com" and "asha@x.com"
  count as the same address. We also always save it in lower case.
- The password is never stored; only its Argon2 hash.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.employees.models import Employee


class RoleName:
    """The three role names from PRD section 4. Use these, never typed strings."""

    ADMIN = "Admin"
    IT_MANAGER = "IT Manager"
    EMPLOYEE = "Employee"

    ALL = (ADMIN, IT_MANAGER, EMPLOYEE)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), unique=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # lazy="joined": load the role/employee together with the user in one query.
    role: Mapped[Role] = relationship(lazy="joined")
    employee: Mapped[Employee | None] = relationship(lazy="joined")

    def __repr__(self) -> str:
        # Never include password_hash here: this text can end up in logs.
        return f"<User id={self.id} email={self.email}>"


# Case-insensitive uniqueness: a unique index on lower(email).
Index("uq_users_email_lower", func.lower(User.email), unique=True)
