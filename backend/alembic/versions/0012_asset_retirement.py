"""Who retired an asset, when, and why - Slice 4.2 (AST-07, BR-13; decisions A3, F2).

- assets.retired_at: when the retirement was saved (UTC).
- assets.retired_by_user_id: the user who retired it (FK users, RESTRICT).
- assets.retire_reason: the required reason (free text, up to 500 characters, A3).
- All three stay empty unless the asset is retired (check constraint). Nothing is
  backfilled: before this slice there was no way to retire an asset, so an asset
  already marked retired by hand keeps them empty and the screen shows "not recorded".
- The `asset.retired` audit row (same transaction) stays the full history (BR-13).

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("retired_by_user_id", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("retire_reason", sa.String(500), nullable=True))
    op.create_foreign_key(
        op.f("fk_assets_retired_by_user_id_users"), "assets", "users",
        ["retired_by_user_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_assets_retired_by_user_id"), "assets", ["retired_by_user_id"])
    op.create_check_constraint(
        op.f("ck_assets_retired_details_only_when_retired"),
        "assets",
        "status = 'retired' OR (retired_at IS NULL AND retired_by_user_id IS NULL AND retire_reason IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_assets_retired_details_only_when_retired"), "assets", type_="check")
    op.drop_index(op.f("ix_assets_retired_by_user_id"), table_name="assets")
    op.drop_constraint(op.f("fk_assets_retired_by_user_id_users"), "assets", type_="foreignkey")
    op.drop_column("assets", "retire_reason")
    op.drop_column("assets", "retired_by_user_id")
    op.drop_column("assets", "retired_at")
