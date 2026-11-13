"""Purchases and purchase lines - Slice 3.1 (PUR-01 to PUR-04, PUR-08, BR-06).

- purchases: system number PUR-000001... (sequence purchase_number_seq, B42),
  vendor, invoice/reference number, purchase date, received date (empty until
  3.2/3.3), notes, status (draft / received / cancelled, PUR-04), created-by user,
  timestamps (UTC).
- Reference number unique per vendor ignoring case among purchases that are not
  cancelled (P3, B43): partial unique index on (vendor_id, lower(reference_number)).
- purchase_lines: line_type 'bulk' -> stock_item_id; 'serialized' -> category_id
  + description (P1). Check constraints enforce exactly one reference matching the
  type, quantity >= 1, unit_cost NUMERIC(12,2) >= 0 (P2), and received_quantity
  empty or 0..quantity (P4).
- All foreign keys are ON DELETE RESTRICT: nothing referenced here is ever deleted (BR-12).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("purchase_number_seq")))
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "purchase_number",
            sa.String(length=20),
            server_default=sa.text("'PUR-' || lpad(nextval('purchase_number_seq')::text, 6, '0')"),
            nullable=False,
        ),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'received', 'cancelled')", name=op.f("ck_purchases_status_valid")),
        sa.CheckConstraint("length(trim(reference_number)) > 0", name=op.f("ck_purchases_reference_not_blank")),
        sa.CheckConstraint(
            "status = 'received' OR received_date IS NULL",
            name=op.f("ck_purchases_received_date_only_when_received"),
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"], ["vendors.id"], name=op.f("fk_purchases_vendor_id_vendors"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name=op.f("fk_purchases_created_by_user_id_users"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchases")),
        sa.UniqueConstraint("purchase_number", name=op.f("uq_purchases_purchase_number")),
    )
    # The sequence belongs to the column: dropped with the table, and reset by
    # TRUNCATE ... RESTART IDENTITY (used by the tests).
    op.execute("ALTER SEQUENCE purchase_number_seq OWNED BY purchases.purchase_number")
    op.create_index(op.f("ix_purchases_vendor_id"), "purchases", ["vendor_id"])
    op.create_index(op.f("ix_purchases_status"), "purchases", ["status"])
    op.create_index(op.f("ix_purchases_created_by_user_id"), "purchases", ["created_by_user_id"])
    op.create_index(
        "uq_purchases_vendor_reference_lower",
        "purchases",
        ["vendor_id", sa.literal_column("lower(reference_number)")],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )

    op.create_table(
        "purchase_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("line_type", sa.String(length=20), nullable=False),
        sa.Column("stock_item_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("received_quantity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("line_type IN ('serialized', 'bulk')", name=op.f("ck_purchase_lines_line_type_valid")),
        sa.CheckConstraint(
            "num_nonnulls(stock_item_id, category_id) = 1", name=op.f("ck_purchase_lines_one_item_reference")
        ),
        sa.CheckConstraint(
            "(line_type = 'bulk' AND stock_item_id IS NOT NULL AND description IS NULL)"
            " OR (line_type = 'serialized' AND category_id IS NOT NULL"
            " AND description IS NOT NULL AND length(trim(description)) > 0)",
            name=op.f("ck_purchase_lines_reference_matches_line_type"),
        ),
        sa.CheckConstraint("quantity >= 1", name=op.f("ck_purchase_lines_quantity_positive")),
        sa.CheckConstraint("unit_cost >= 0", name=op.f("ck_purchase_lines_unit_cost_not_negative")),
        sa.CheckConstraint(
            "received_quantity IS NULL OR (received_quantity >= 0 AND received_quantity <= quantity)",
            name=op.f("ck_purchase_lines_received_quantity_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"], ["purchases.id"],
            name=op.f("fk_purchase_lines_purchase_id_purchases"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_item_id"], ["stock_items.id"],
            name=op.f("fk_purchase_lines_stock_item_id_stock_items"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["asset_categories.id"],
            name=op.f("fk_purchase_lines_category_id_asset_categories"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_lines")),
    )
    op.create_index(op.f("ix_purchase_lines_purchase_id"), "purchase_lines", ["purchase_id"])
    op.create_index(op.f("ix_purchase_lines_stock_item_id"), "purchase_lines", ["stock_item_id"])
    op.create_index(op.f("ix_purchase_lines_category_id"), "purchase_lines", ["category_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_lines_category_id"), table_name="purchase_lines")
    op.drop_index(op.f("ix_purchase_lines_stock_item_id"), table_name="purchase_lines")
    op.drop_index(op.f("ix_purchase_lines_purchase_id"), table_name="purchase_lines")
    op.drop_table("purchase_lines")
    op.drop_index("uq_purchases_vendor_reference_lower", table_name="purchases")
    op.drop_index(op.f("ix_purchases_created_by_user_id"), table_name="purchases")
    op.drop_index(op.f("ix_purchases_status"), table_name="purchases")
    op.drop_index(op.f("ix_purchases_vendor_id"), table_name="purchases")
    op.drop_table("purchases")  # also drops purchase_number_seq (OWNED BY)
    op.execute("DROP SEQUENCE IF EXISTS purchase_number_seq")
