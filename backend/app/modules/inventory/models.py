"""The stock_items table: items tracked BY QUANTITY (Slice 2.4, INV-01, PRD 9.2),
and stock_movements: the append-only history of every balance change (Slice 3.3, INV-05).

KEY RULE (PRD 9.2): an item is tracked one by one (an asset) OR by quantity (a
stock item), never both. A stock item belongs to a category whose
tracking_type is 'bulk'; laptops and monitors ('serialized') are never stock items.

- unit_of_measure: one of UNITS (fixed list, decision B35).
- reorder_threshold: required, >= 0 (B37). Low stock = quantity at or below it (INV-06, Slice 4.3).
- quantity_on_hand: the current BALANCE, >= 0 (INV-07). It starts at 0 and is
  NEVER set directly: only stock movements change it (receiving 3.3,
  issue/adjust 4.4, opening stock 4.5), in the same transaction as the movement
  row, so balance and history always match (B39).
- Never deleted, only deactivated (BR-12, gap 2), and only at zero stock (B38).
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    event,
    func,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.categories.models import AssetCategory

if TYPE_CHECKING:
    from app.modules.users.models import User


class StockItemStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"

    ALL = (ACTIVE, INACTIVE)


# Fixed list of units (B35). Adding one later = a small migration changing the check constraint.
UNITS = ("pieces", "boxes", "packs", "pairs", "sets", "rolls", "metres")

NAME_MAX_LENGTH = 150


class StockItem(TimestampMixin, Base):
    __tablename__ = "stock_items"
    __table_args__ = (
        CheckConstraint(
            "unit_of_measure IN ('pieces', 'boxes', 'packs', 'pairs', 'sets', 'rolls', 'metres')",
            name="unit_valid",
        ),
        CheckConstraint("reorder_threshold >= 0", name="reorder_threshold_not_negative"),
        CheckConstraint("quantity_on_hand >= 0", name="quantity_not_negative"),
        CheckConstraint("status IN ('active', 'inactive')", name="status_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("asset_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    reorder_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StockItemStatus.ACTIVE, server_default=StockItemStatus.ACTIVE
    )

    category: Mapped[AssetCategory] = relationship(lazy="joined")

    @property
    def low_stock(self) -> bool:
        """Low stock (INV-06, Slice 4.3): an ACTIVE item whose quantity on hand is at or
        below its reorder threshold (B37: a threshold of 0 warns only when stock runs out).
        Inactive items are never flagged: they always have 0 and cannot be restocked (G1)."""
        return self.status == StockItemStatus.ACTIVE and self.quantity_on_hand <= self.reorder_threshold

    @classmethod
    def low_stock_condition(cls):
        """The same rule as `low_stock`, for SQL filters."""
        return (cls.status == StockItemStatus.ACTIVE) & (cls.quantity_on_hand <= cls.reorder_threshold)

    @property
    def is_active(self) -> bool:
        return self.status == StockItemStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<StockItem {self.id} {self.name}>"


# Name unique within its category, ignoring case (migration 0007).
Index("uq_stock_items_category_name_lower", StockItem.category_id, func.lower(StockItem.name), unique=True)


# ---- Stock movements (Slice 3.3, INV-03, INV-05, BR-09) ----------------------------------
class MovementType:
    """P7. Quantity is always > 0; the type says whether stock goes in or out."""

    RECEIPT = "receipt"  # purchase received (3.3)
    ISSUE = "issue"  # handed out / consumed (4.4)
    ADJUSTMENT_IN = "adjustment_in"  # correction up (4.4)
    ADJUSTMENT_OUT = "adjustment_out"  # correction down (4.4)
    OPENING = "opening"  # one-time opening stock (4.5)

    ALL = (RECEIPT, ISSUE, ADJUSTMENT_IN, ADJUSTMENT_OUT, OPENING)
    INCOMING = frozenset({RECEIPT, ADJUSTMENT_IN, OPENING})
    OUTGOING = frozenset({ISSUE, ADJUSTMENT_OUT})


REASON_MAX_LENGTH = 500


class StockMovement(Base):
    """One change to a stock item's balance. APPEND-ONLY: never changed or deleted
    (guard below + database trigger, migration 0010). Only created through
    inventory.service.record_movement(), which also updates quantity_on_hand in the
    same transaction (B39)."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('receipt', 'issue', 'adjustment_in', 'adjustment_out', 'opening')",
            name="movement_type_valid",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("balance_after >= 0", name="balance_after_not_negative"),
        CheckConstraint(
            "(movement_type = 'receipt') = (purchase_line_id IS NOT NULL)",
            name="receipt_has_purchase_line",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(
        ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    purchase_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_lines.id", ondelete="RESTRICT"), index=True
    )
    reason: Mapped[str | None] = mapped_column(String(REASON_MAX_LENGTH))
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    stock_item: Mapped[StockItem] = relationship()
    created_by: Mapped["User"] = relationship(lazy="joined")  # the responsible user (BR-09)

    def __repr__(self) -> str:
        return f"<StockMovement {self.id} {self.movement_type} {self.quantity} item={self.stock_item_id}>"


# ---- Append-only guard in the application (the trigger is the final guard) ----------------
@event.listens_for(Session, "before_flush")
def _block_movement_changes(session: Session, _flush_context: Any, _instances: Any) -> None:
    for obj in session.deleted:
        if isinstance(obj, StockMovement):
            raise PermissionError("Stock movements can never be deleted.")
    for obj in session.dirty:
        if isinstance(obj, StockMovement) and session.is_modified(obj):
            raise PermissionError("Stock movements can never be changed.")
