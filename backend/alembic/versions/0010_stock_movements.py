"""Stock movements (append-only history of bulk stock) - Slice 3.3 (INV-03, INV-05, BR-09, B39).

- stock_movements: which stock item, movement type (receipt / issue /
  adjustment_in / adjustment_out / opening, P7), quantity (> 0; the type says
  whether it goes in or out), the balance after the movement (C4), the business
  date (movement_date, e.g. the received date, C2), when it was saved
  (created_at, UTC), the responsible user, the purchase line for a receipt, and
  an optional reason (C3: required for adjustments from Slice 4.4).
- A receipt always points at its purchase line; other types never do.
- A trigger rejects any UPDATE or DELETE: history cannot be rewritten.
  (TRUNCATE is still possible for an administrator, e.g. on the test database.)
- All foreign keys are ON DELETE RESTRICT.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("stock_item_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("purchase_line_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "movement_type IN ('receipt', 'issue', 'adjustment_in', 'adjustment_out', 'opening')",
            name=op.f("ck_stock_movements_movement_type_valid"),
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_stock_movements_quantity_positive")),
        sa.CheckConstraint("balance_after >= 0", name=op.f("ck_stock_movements_balance_after_not_negative")),
        sa.CheckConstraint(
            "(movement_type = 'receipt') = (purchase_line_id IS NOT NULL)",
            name=op.f("ck_stock_movements_receipt_has_purchase_line"),
        ),
        sa.ForeignKeyConstraint(
            ["stock_item_id"], ["stock_items.id"],
            name=op.f("fk_stock_movements_stock_item_id_stock_items"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_line_id"], ["purchase_lines.id"],
            name=op.f("fk_stock_movements_purchase_line_id_purchase_lines"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name=op.f("fk_stock_movements_created_by_user_id_users"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_movements")),
    )
    op.create_index(op.f("ix_stock_movements_stock_item_id"), "stock_movements", ["stock_item_id"])
    op.create_index(op.f("ix_stock_movements_purchase_line_id"), "stock_movements", ["purchase_line_id"])
    op.create_index(op.f("ix_stock_movements_created_by_user_id"), "stock_movements", ["created_by_user_id"])
    op.create_index(op.f("ix_stock_movements_movement_date"), "stock_movements", ["movement_date"])

    # Append-only guard in the database itself.
    op.execute(
        """
        CREATE FUNCTION stock_movements_block_changes() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'stock_movements is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_stock_movements_append_only
        BEFORE UPDATE OR DELETE ON stock_movements
        FOR EACH ROW EXECUTE FUNCTION stock_movements_block_changes();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_stock_movements_append_only ON stock_movements")
    op.execute("DROP FUNCTION IF EXISTS stock_movements_block_changes()")
    op.drop_index(op.f("ix_stock_movements_movement_date"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_created_by_user_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_purchase_line_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_stock_item_id"), table_name="stock_movements")
    op.drop_table("stock_movements")
