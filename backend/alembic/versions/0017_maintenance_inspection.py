"""Completion inspection - Slice 6.3 (MNT-07, workflow 7.4; owner's answers in decisions.md section 35).

Adds to maintenance_requests (every new column may be empty, so existing rows stay valid;
no existing row is changed):
- inspection_outcome (available / damaged / retired), inspection_date (business date),
  inspection_notes (up to 1,000), inspected_at (database time), inspected_by_user_id
Check constraints: the five are filled together; only a Completed request, or one Cancelled after
work started, can carry an inspection; notes are required for Damaged and Retired; the inspection
date is not before the completion date.

The partial unique index uq_maintenance_requests_open_asset is widened (owner's answer, revises O2):
an asset has at most ONE request that is Reported, In Progress, or awaiting inspection (work
started, and not yet inspected).

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here (not imported) so this migration never changes when the app code does.
INSPECTED_TOGETHER = "(inspection_outcome IS NULL AND inspection_date IS NULL AND inspected_at IS NULL AND inspected_by_user_id IS NULL AND inspection_notes IS NULL) OR (inspection_outcome IS NOT NULL AND inspection_date IS NOT NULL AND inspected_at IS NOT NULL AND inspected_by_user_id IS NOT NULL)"
INSPECTED_MATCHES_STATUS = "inspected_at IS NULL OR (status IN ('completed', 'cancelled') AND started_at IS NOT NULL)"
INSPECTION_OUTCOME_VALID = "inspection_outcome IS NULL OR inspection_outcome IN ('available', 'damaged', 'retired')"
INSPECTION_NOTES_REQUIRED = "inspection_outcome IS NULL OR inspection_outcome = 'available' OR inspection_notes IS NOT NULL"
INSPECTION_NOT_BEFORE_COMPLETION = "inspection_date IS NULL OR completion_date IS NULL OR inspection_date >= completion_date"

OLD_OPEN_WHERE = "status IN ('reported', 'in_progress')"
NEW_OPEN_WHERE = "status = 'reported' OR (started_at IS NOT NULL AND inspected_at IS NULL)"
INDEX = "uq_maintenance_requests_open_asset"

TABLE = "maintenance_requests"
CHECKS = {
    "inspected_together": INSPECTED_TOGETHER,
    "inspected_matches_status": INSPECTED_MATCHES_STATUS,
    "inspection_outcome_valid": INSPECTION_OUTCOME_VALID,
    "inspection_notes_required": INSPECTION_NOTES_REQUIRED,
    "inspection_not_before_completion": INSPECTION_NOT_BEFORE_COMPLETION,
}


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("inspection_outcome", sa.String(length=20), nullable=True))
    op.add_column(TABLE, sa.Column("inspection_date", sa.Date(), nullable=True))
    op.add_column(TABLE, sa.Column("inspection_notes", sa.String(length=1000), nullable=True))
    op.add_column(TABLE, sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(TABLE, sa.Column("inspected_by_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f(f"fk_{TABLE}_inspected_by_user_id_users"), TABLE, "users", ["inspected_by_user_id"], ["id"],
        ondelete="RESTRICT",
    )
    for name, condition in CHECKS.items():
        op.create_check_constraint(op.f(f"ck_{TABLE}_{name}"), TABLE, condition)
    op.drop_index(INDEX, table_name=TABLE)
    op.create_index(INDEX, TABLE, ["asset_id"], unique=True, postgresql_where=sa.text(NEW_OPEN_WHERE))


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)
    op.create_index(INDEX, TABLE, ["asset_id"], unique=True, postgresql_where=sa.text(OLD_OPEN_WHERE))
    for name in reversed(list(CHECKS)):
        op.drop_constraint(op.f(f"ck_{TABLE}_{name}"), TABLE, type_="check")
    op.drop_constraint(op.f(f"fk_{TABLE}_inspected_by_user_id_users"), TABLE, type_="foreignkey")
    for column in ("inspected_by_user_id", "inspected_at", "inspection_notes", "inspection_date", "inspection_outcome"):
        op.drop_column(TABLE, column)
