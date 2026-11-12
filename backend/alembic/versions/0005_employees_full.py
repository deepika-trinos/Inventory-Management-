"""Employees: full record - Slice 2.2 (EMP-01 to EMP-03, BR-12).

EXTENDS the minimal employees table from 0002 (existing rows are kept):
- new optional columns: department, designation, phone (contact details).
- work_email: existing values are trimmed and stored in lower case (B5), then
  made unique ignoring case (unique index on lower(work_email); empty is allowed
  for many employees).
- employee_code: uniqueness becomes case-insensitive ("EMP-001" = "emp-001"):
  the plain unique constraint is replaced by a unique index on lower(employee_code),
  which also serves searching by code.
- search indexes on lower(full_name) and lower(department).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("department", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("designation", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("phone", sa.String(length=30), nullable=True))

    # Clean existing data so the new unique indexes can be built.
    op.execute("UPDATE employees SET employee_code = trim(employee_code), full_name = trim(full_name)")
    op.execute("UPDATE employees SET work_email = NULLIF(lower(trim(work_email)), '')")

    op.drop_constraint("uq_employees_employee_code", "employees", type_="unique")
    op.create_index(
        "uq_employees_employee_code_lower", "employees",
        [sa.literal_column("lower(employee_code)")], unique=True,
    )
    op.create_index(
        "uq_employees_work_email_lower", "employees",
        [sa.literal_column("lower(work_email)")], unique=True,
    )
    op.create_index("ix_employees_full_name_lower", "employees", [sa.literal_column("lower(full_name)")])
    op.create_index("ix_employees_department_lower", "employees", [sa.literal_column("lower(department)")])


def downgrade() -> None:
    op.drop_index("ix_employees_department_lower", table_name="employees")
    op.drop_index("ix_employees_full_name_lower", table_name="employees")
    op.drop_index("uq_employees_work_email_lower", table_name="employees")
    op.drop_index("uq_employees_employee_code_lower", table_name="employees")
    op.create_unique_constraint("uq_employees_employee_code", "employees", ["employee_code"])
    op.drop_column("employees", "phone")
    op.drop_column("employees", "designation")
    op.drop_column("employees", "department")
