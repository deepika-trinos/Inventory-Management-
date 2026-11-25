"""Maintenance progress - Slice 6.2 (MNT-04 to MNT-07; owner's answers S1-S14; decision U1).

Adds to maintenance_requests (every new column may be empty, so existing rows stay valid;
no existing row is changed):
- start work: started_date, started_at, started_by_user_id
- details: service_provider (up to 200), repair_notes (up to 1,000), cost (NUMERIC(12,2), 0 or more)
- completed: completion_date, completed_at, completed_by_user_id
- cancelled: cancelled_at, cancelled_by_user_id, cancel_reason (up to 500)
Check constraints keep each group consistent with the request's status.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Written out here (not imported) so this migration never changes when the app code does.
STARTED_TOGETHER = '(started_date IS NULL AND started_at IS NULL AND started_by_user_id IS NULL) OR (started_date IS NOT NULL AND started_at IS NOT NULL AND started_by_user_id IS NOT NULL)'
STARTED_MATCHES_STATUS = "(status = 'reported' AND started_at IS NULL) OR (status IN ('in_progress', 'completed') AND started_at IS NOT NULL) OR status = 'cancelled'"
COMPLETED_MATCHES_STATUS = "(status = 'completed' AND completion_date IS NOT NULL AND completed_at IS NOT NULL AND completed_by_user_id IS NOT NULL AND repair_notes IS NOT NULL) OR (status <> 'completed' AND completion_date IS NULL AND completed_at IS NULL AND completed_by_user_id IS NULL)"
CANCELLED_MATCHES_STATUS = "(status = 'cancelled' AND cancelled_at IS NOT NULL AND cancelled_by_user_id IS NOT NULL AND cancel_reason IS NOT NULL) OR (status <> 'cancelled' AND cancelled_at IS NULL AND cancelled_by_user_id IS NULL AND cancel_reason IS NULL)"

TABLE = "maintenance_requests"
USER_COLUMNS = ("started_by_user_id", "completed_by_user_id", "cancelled_by_user_id")
CHECKS = {
    "started_together": STARTED_TOGETHER,
    "started_matches_status": STARTED_MATCHES_STATUS,
    "completed_matches_status": COMPLETED_MATCHES_STATUS,
    "cancelled_matches_status": CANCELLED_MATCHES_STATUS,
    "cost_not_negative": "cost IS NULL OR cost >= 0",
    "started_not_before_reported": "started_date IS NULL OR started_date >= reported_date",
    "completion_not_before_start": "completion_date IS NULL OR completion_date >= started_date",
}


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("started_date", sa.Date(), nullable=True))
    op.add_column(TABLE, sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(TABLE, sa.Column("started_by_user_id", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("service_provider", sa.String(length=200), nullable=True))
    op.add_column(TABLE, sa.Column("repair_notes", sa.String(length=1000), nullable=True))
    op.add_column(TABLE, sa.Column("cost", sa.Numeric(12, 2), nullable=True))
    op.add_column(TABLE, sa.Column("completion_date", sa.Date(), nullable=True))
    op.add_column(TABLE, sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(TABLE, sa.Column("completed_by_user_id", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(TABLE, sa.Column("cancelled_by_user_id", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("cancel_reason", sa.String(length=500), nullable=True))
    for column in USER_COLUMNS:
        op.create_foreign_key(
            op.f(f"fk_{TABLE}_{column}_users"), TABLE, "users", [column], ["id"], ondelete="RESTRICT"
        )
    for name, condition in CHECKS.items():
        op.create_check_constraint(op.f(f"ck_{TABLE}_{name}"), TABLE, condition)


def downgrade() -> None:
    for name in reversed(list(CHECKS)):
        op.drop_constraint(op.f(f"ck_{TABLE}_{name}"), TABLE, type_="check")
    for column in reversed(USER_COLUMNS):
        op.drop_constraint(op.f(f"fk_{TABLE}_{column}_users"), TABLE, type_="foreignkey")
    for column in (
        "cancel_reason", "cancelled_by_user_id", "cancelled_at", "completed_by_user_id", "completed_at",
        "completion_date", "cost", "repair_notes", "service_provider", "started_by_user_id", "started_at",
        "started_date",
    ):
        op.drop_column(TABLE, column)
