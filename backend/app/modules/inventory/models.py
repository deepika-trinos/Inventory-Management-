"""The stock_items table: items tracked BY QUANTITY (Slice 2.4, INV-01, PRD 9.2).

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

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.categories.models import AssetCategory


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
    def is_active(self) -> bool:
        return self.status == StockItemStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<StockItem {self.id} {self.name}>"


# Name unique within its category, ignoring case (migration 0007).
Index("uq_stock_items_category_name_lower", StockItem.category_id, func.lower(StockItem.name), unique=True)
