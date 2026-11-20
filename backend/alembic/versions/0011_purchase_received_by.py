"""Who received a purchase, and when it was saved - Slice 3.4 (PUR-09, BR-13, decision D1).

- purchases.received_by_user_id: the user who received it (FK users, RESTRICT).
- purchases.received_at: when the receipt was saved (UTC). The business date stays
  in received_date (C2).
- Both are empty unless the purchase is received (check constraint).
- Purchases received before this migration (Slices 3.2-3.3) are filled from their
  `purchase.received` audit row (actor and time). A received purchase without
  such a row keeps both empty and the screen shows "not recorded".

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("purchases", sa.Column("received_by_user_id", sa.Integer(), nullable=True))
    op.add_column("purchases", sa.Column("received_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_purchases_received_by_user_id_users"), "purchases", "users",
        ["received_by_user_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_purchases_received_by_user_id"), "purchases", ["received_by_user_id"])

    # Backfill from the audit log (the latest purchase.received row per purchase).
    op.execute(
        """
        UPDATE purchases AS p
           SET received_by_user_id = a.actor_user_id,
               received_at = a.created_at
          FROM (
                SELECT DISTINCT ON (entity_id) entity_id, actor_user_id, created_at
                  FROM audit_logs
                 WHERE action = 'purchase.received' AND entity_type = 'purchases'
                 ORDER BY entity_id, id DESC
               ) AS a
         WHERE p.status = 'received' AND a.entity_id = p.id::text
        """
    )

    op.create_check_constraint(
        op.f("ck_purchases_received_by_only_when_received"),
        "purchases",
        "status = 'received' OR (received_by_user_id IS NULL AND received_at IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_purchases_received_by_only_when_received"), "purchases", type_="check")
    op.drop_index(op.f("ix_purchases_received_by_user_id"), table_name="purchases")
    op.drop_constraint(op.f("fk_purchases_received_by_user_id_users"), "purchases", type_="foreignkey")
    op.drop_column("purchases", "received_at")
    op.drop_column("purchases", "received_by_user_id")
