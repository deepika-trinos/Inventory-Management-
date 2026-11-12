"""Bulk stock items - Slice 2.4 (INV-01, BR-12, INV-07, PRD 9.2).

- stock_items: name, category (must be an active 'bulk' category, checked in
  the service), unit_of_measure (fixed list, decision B35), reorder_threshold
  (>= 0, required, B37), quantity_on_hand (>= 0, starts at 0), status, timestamps.
- PRD 9.2: bulk stock is stored as a BALANCE (quantity_on_hand) that only stock
  movements change (Slices 3.3, 4.4, 4.5), each in the same transaction as its
  movement row, so the two always match (B39).
- name is unique within its category ignoring case: unique index on
  (category_id, lower(name)).
- category_id: ON DELETE RESTRICT (categories are never deleted anyway, BR-12).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UNITS = ("pieces", "boxes", "packs", "pairs", "sets", "rolls", "metres")


def upgrade() -> None:
    units_sql = ", ".join(f"'{u}'" for u in UNITS)
    op.create_table(
        "stock_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=20), nullable=False),
        sa.Column("reorder_threshold", sa.Integer(), nullable=False),
        sa.Column("quantity_on_hand", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"unit_of_measure IN ({units_sql})", name=op.f("ck_stock_items_unit_valid")),
        sa.CheckConstraint("reorder_threshold >= 0", name=op.f("ck_stock_items_reorder_threshold_not_negative")),
        sa.CheckConstraint("quantity_on_hand >= 0", name=op.f("ck_stock_items_quantity_not_negative")),
        sa.CheckConstraint("status IN ('active', 'inactive')", name=op.f("ck_stock_items_status_valid")),
        sa.ForeignKeyConstraint(
            ["category_id"], ["asset_categories.id"],
            name=op.f("fk_stock_items_category_id_asset_categories"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_items")),
    )
    op.create_index(op.f("ix_stock_items_category_id"), "stock_items", ["category_id"])
    op.create_index(
        "uq_stock_items_category_name_lower", "stock_items",
        ["category_id", sa.literal_column("lower(name)")], unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_stock_items_category_name_lower", table_name="stock_items")
    op.drop_index(op.f("ix_stock_items_category_id"), table_name="stock_items")
    op.drop_table("stock_items")
