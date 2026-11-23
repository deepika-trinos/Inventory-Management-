"""Who received issued stock - Slice 4.4 (INV-04, BR-09; owner's answer A4).

- stock_movements.issued_to_employee_id: the employee an ISSUE went to (FK employees,
  RESTRICT). Optional: issues to a room, event or team name no employee (A4).
- Only an issue may name an employee (check constraint); receipts, adjustments and
  opening stock never do.
- Adding a column changes no existing row (every row gets NULL), so the append-only
  rule for movements (migration 0010) is untouched.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("stock_movements", sa.Column("issued_to_employee_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_stock_movements_issued_to_employee_id_employees"), "stock_movements", "employees",
        ["issued_to_employee_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_stock_movements_issued_to_employee_id"), "stock_movements", ["issued_to_employee_id"])
    op.create_check_constraint(
        op.f("ck_stock_movements_employee_only_on_issue"),
        "stock_movements",
        "movement_type = 'issue' OR issued_to_employee_id IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_stock_movements_employee_only_on_issue"), "stock_movements", type_="check")
    op.drop_index(op.f("ix_stock_movements_issued_to_employee_id"), table_name="stock_movements")
    op.drop_constraint(op.f("fk_stock_movements_issued_to_employee_id_employees"), "stock_movements", type_="foreignkey")
    op.drop_column("stock_movements", "issued_to_employee_id")
