"""Assignments - Slice 5.1 (ASN-01 to ASN-04, BR-02, BR-03, BR-05, BR-11; owner's answers N1-N3).

- assignments: one row each time an asset is given to an employee: asset, employee,
  assignment date, optional expected return date (on or after the assignment date),
  who assigned it, when it was saved.
- Return fields (return date, outcome, condition notes, returned at / by) are empty
  until Slice 5.2 fills them (N4); a check constraint keeps the required ones together.
- uq_assignments_open_asset: a PARTIAL unique index, so an asset can have only ONE
  open (not returned) assignment, even if two people assign it at the same moment.
- A new table only: no existing row is changed.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("assignment_date", sa.Date(), nullable=False),
        sa.Column("expected_return_date", sa.Date(), nullable=True),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("return_outcome", sa.String(length=30), nullable=True),
        sa.Column("condition_notes", sa.String(length=1000), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "expected_return_date IS NULL OR expected_return_date >= assignment_date",
            name=op.f("ck_assignments_expected_return_not_before_assignment"),
        ),
        sa.CheckConstraint(
            "(returned_at IS NULL AND return_date IS NULL AND return_outcome IS NULL"
            " AND returned_by_user_id IS NULL AND condition_notes IS NULL)"
            " OR (returned_at IS NOT NULL AND return_date IS NOT NULL AND return_outcome IS NOT NULL"
            " AND returned_by_user_id IS NOT NULL)",
            name=op.f("ck_assignments_return_details_together"),
        ),
        sa.CheckConstraint(
            "return_date IS NULL OR return_date >= assignment_date",
            name=op.f("ck_assignments_return_not_before_assignment"),
        ),
        sa.CheckConstraint(
            "return_outcome IS NULL OR return_outcome IN ('available', 'under_maintenance', 'damaged')",
            name=op.f("ck_assignments_return_outcome_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_assignments_asset_id_assets"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("fk_assignments_employee_id_employees"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"], ["users.id"], name=op.f("fk_assignments_assigned_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["returned_by_user_id"], ["users.id"], name=op.f("fk_assignments_returned_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignments")),
    )
    op.create_index(op.f("ix_assignments_asset_id"), "assignments", ["asset_id"])
    op.create_index(op.f("ix_assignments_employee_id"), "assignments", ["employee_id"])
    op.create_index(op.f("ix_assignments_assigned_by_user_id"), "assignments", ["assigned_by_user_id"])
    op.create_index(op.f("ix_assignments_returned_by_user_id"), "assignments", ["returned_by_user_id"])
    op.create_index(
        "uq_assignments_open_asset", "assignments", ["asset_id"], unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_assignments_open_asset", table_name="assignments")
    op.drop_index(op.f("ix_assignments_returned_by_user_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_assigned_by_user_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_employee_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_asset_id"), table_name="assignments")
    op.drop_table("assignments")
