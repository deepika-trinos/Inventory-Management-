"""The purchases and purchase_lines tables (Slice 3.1, PUR-01 to PUR-04, PUR-08, BR-06).

A purchase is created as a DRAFT. Only receiving (Slices 3.2 / 3.3) changes stock
or creates assets; a draft or cancelled purchase never does (PUR-08, BR-06).

purchases
- purchase_number: made by the system, PUR-000001, PUR-000002, ... (decision B42),
  from the database sequence purchase_number_seq. Read-only.
- reference_number: the vendor's invoice / reference number. Required; unique per
  vendor ignoring case among purchases that are NOT cancelled (P3, B43).
- purchase_date: cannot be in the future (P3; checked in the service, company timezone).
- received_date: empty until the purchase is received (3.2 / 3.3).
- status: draft -> received (3.2 / 3.3) or draft -> cancelled (3.1). Received and
  cancelled are final (P6). Purchases are never deleted (BR-12).

purchase_lines (P1)
- 'bulk' line       -> stock_item_id (an item tracked by quantity), no category, no description.
- 'serialized' line -> category_id (a one-by-one category) + a typed description,
                       e.g. "Laptops: Dell Latitude 5440".
  Exactly one of stock_item_id / category_id is set, matching line_type (check constraints).
- quantity: whole number >= 1. unit_cost: NUMERIC(12,2) in INR, 0 allowed (P2).
- received_quantity: empty until received; then 0..quantity (P4: lower allowed, never higher).
- Line totals and the purchase total are CALCULATED (quantity x unit cost), never stored or typed.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.categories.models import AssetCategory
from app.modules.inventory.models import StockItem, StockMovement
from app.modules.users.models import User
from app.modules.vendors.models import Vendor

if TYPE_CHECKING:
    from app.modules.assets.models import Asset


class PurchaseStatus:
    DRAFT = "draft"
    RECEIVED = "received"
    CANCELLED = "cancelled"

    ALL = (DRAFT, RECEIVED, CANCELLED)


class LineType:
    SERIALIZED = "serialized"  # one by one: becomes assets when received (3.2)
    BULK = "bulk"  # by quantity: raises a stock item's balance when received (3.3)

    ALL = (SERIALIZED, BULK)


REFERENCE_MAX_LENGTH = 100
NOTES_MAX_LENGTH = 2000
DESCRIPTION_MAX_LENGTH = 200
PURCHASE_NUMBER_PREFIX = "PUR-"

# The sequence behind PUR-000001, PUR-000002, ... (migration 0008). Owned by
# purchases.purchase_number, so it is dropped with the table.
purchase_number_seq = Sequence("purchase_number_seq", metadata=Base.metadata)


class Purchase(TimestampMixin, Base):
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'received', 'cancelled')", name="status_valid"),
        CheckConstraint("length(trim(reference_number)) > 0", name="reference_not_blank"),
        CheckConstraint("status = 'received' OR received_date IS NULL", name="received_date_only_when_received"),
        CheckConstraint(
            "status = 'received' OR (received_by_user_id IS NULL AND received_at IS NULL)",
            name="received_by_only_when_received",
        ),
    )
    # Read the database-made purchase_number back right after the INSERT.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        server_default=text("'PUR-' || lpad(nextval('purchase_number_seq')::text, 6, '0')"),
    )
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True)
    reference_number: Mapped[str] = mapped_column(String(REFERENCE_MAX_LENGTH), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(NOTES_MAX_LENGTH))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PurchaseStatus.DRAFT, server_default=PurchaseStatus.DRAFT, index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Who received it and when the receipt was saved (UTC); empty unless received
    # (Slice 3.4, D1; migration 0011 filled them in for older receipts from the audit log).
    received_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vendor: Mapped[Vendor] = relationship(lazy="joined")
    created_by: Mapped[User] = relationship(lazy="joined", foreign_keys=[created_by_user_id])
    received_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[received_by_user_id])
    lines: Mapped[list["PurchaseLine"]] = relationship(
        back_populates="purchase",
        lazy="selectin",
        order_by="PurchaseLine.id",
        cascade="all, delete-orphan",  # removing a line from a DRAFT deletes that line row
    )

    @property
    def is_draft(self) -> bool:
        return self.status == PurchaseStatus.DRAFT

    @property
    def total_amount(self) -> Decimal:
        return sum((line.line_total for line in self.lines), Decimal("0.00"))

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def __repr__(self) -> str:
        return f"<Purchase {self.purchase_number} {self.status}>"


class PurchaseLine(TimestampMixin, Base):
    __tablename__ = "purchase_lines"
    __table_args__ = (
        CheckConstraint("line_type IN ('serialized', 'bulk')", name="line_type_valid"),
        # Exactly one of stock_item_id / category_id ...
        CheckConstraint("num_nonnulls(stock_item_id, category_id) = 1", name="one_item_reference"),
        # ... and it is the one that matches the line type (P1).
        CheckConstraint(
            "(line_type = 'bulk' AND stock_item_id IS NOT NULL AND description IS NULL)"
            " OR (line_type = 'serialized' AND category_id IS NOT NULL"
            " AND description IS NOT NULL AND length(trim(description)) > 0)",
            name="reference_matches_line_type",
        ),
        CheckConstraint("quantity >= 1", name="quantity_positive"),
        CheckConstraint("unit_cost >= 0", name="unit_cost_not_negative"),
        CheckConstraint(
            "received_quantity IS NULL OR (received_quantity >= 0 AND received_quantity <= quantity)",
            name="received_quantity_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    line_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_items.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_categories.id", ondelete="RESTRICT"), index=True
    )
    description: Mapped[str | None] = mapped_column(String(DESCRIPTION_MAX_LENGTH))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_quantity: Mapped[int | None] = mapped_column(Integer)

    purchase: Mapped[Purchase] = relationship(back_populates="lines")
    stock_item: Mapped[StockItem | None] = relationship(lazy="joined")
    category: Mapped[AssetCategory | None] = relationship(lazy="joined")
    # The assets created when this one-by-one line was received (Slice 3.2, PUR-06).
    assets: Mapped[list["Asset"]] = relationship(back_populates="purchase_line", lazy="selectin", order_by="Asset.id")
    # The stock movements written when this by-quantity line was received (Slice 3.3; shown from 3.4).
    stock_movements: Mapped[list[StockMovement]] = relationship(
        lazy="selectin", order_by=StockMovement.id, viewonly=True
    )

    @property
    def line_total(self) -> Decimal:
        """quantity x unit cost, in INR with 2 decimals (calculated, never stored)."""
        return (Decimal(self.quantity) * Decimal(self.unit_cost)).quantize(Decimal("0.01"))

    def __repr__(self) -> str:
        return f"<PurchaseLine {self.id} {self.line_type} x{self.quantity}>"


# Invoice / reference number unique per vendor, ignoring case, among purchases that
# are not cancelled (P3, B43): a cancelled purchase frees its number. Migration 0008.
Index(
    "uq_purchases_vendor_reference_lower",
    Purchase.vendor_id,
    func.lower(Purchase.reference_number),
    unique=True,
    postgresql_where=text("status <> 'cancelled'"),
)
