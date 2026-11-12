"""Asset categories - Slice 2.1 (AST-02, PRD 9.2).

- asset_categories: name, optional description, tracking_type and status.
- name is unique ignoring upper/lower case (unique index on lower(name)), so
  "Laptops" and "laptops" cannot both exist - active or inactive.
- tracking_type: 'serialized' (tracked one by one, e.g. laptops) or 'bulk'
  (tracked by quantity, e.g. mice). Enforced by a check constraint (PRD 9.2).
- status: 'active' or 'inactive'. Categories are never deleted (BR-12,
  decisions.md gap 2), only deactivated.
- Timestamps are "timestamp with time zone" and stored in UTC.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("tracking_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "tracking_type IN ('serialized', 'bulk')",
            name=op.f("ck_asset_categories_tracking_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name=op.f("ck_asset_categories_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_categories")),
    )
    op.create_index(
        "uq_asset_categories_name_lower",
        "asset_categories",
        [sa.literal_column("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_asset_categories_name_lower", table_name="asset_categories")
    op.drop_table("asset_categories")
