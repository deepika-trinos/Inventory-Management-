"""The assets table: equipment tracked ONE BY ONE (Slice 3.2, AST-01, AST-02, AST-06, BR-01, BR-08).

KEY RULE (PRD 9.2, BR-08): every physical unit of a one-by-one category (laptops,
monitors, ...) is its own asset record with its own ID. These units are never
also counted as stock (stock_items are for "by quantity" categories only).

- asset_code: made by the system, AST-000001, AST-000002, ... (Q3, BR-01), from the
  database sequence asset_code_seq, so two receipts saved at the same moment can
  never get the same ID. Read-only. A save that fails after a number was taken
  leaves a gap (numbers are never reused).
- serial_number: required, unique across ALL assets ignoring case (AST-06, P5),
  enforced by the unique index uq_assets_serial_number_lower.
- model: required; brand, warranty_expiry and location (typed text, Q1) optional (P5).
- name: required; when received it starts as the purchase line's description (B57).
- purchase_line_id / purchase_date / cost: where the asset came from (AST-02).
  Empty for equipment the company already owned (manual entry, Slice 4.5).
- status (PRD 8.1): available, assigned, under_maintenance, damaged, retired.
  New assets start as AVAILABLE. Status changes only through actions (AST-07):
  assign / return (Phase 5), maintenance (Phase 6), retire (Slice 4.2).
- Never deleted (BR-12): a wrong asset is retired (Slice 4.2, P6).
- retired_at / retired_by_user_id / retire_reason (Slice 4.2, migration 0012, F2):
  who retired it, when, and why. Empty unless the asset is retired (check constraint).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, Sequence, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.categories.models import AssetCategory
from app.modules.users.models import User

if TYPE_CHECKING:
    from app.modules.purchases.models import PurchaseLine


class AssetStatus:
    """PRD 8.1. Stored in lower case; the screen shows "Under Maintenance" etc."""

    AVAILABLE = "available"  # usable and can be assigned
    ASSIGNED = "assigned"  # with an employee (Phase 5)
    UNDER_MAINTENANCE = "under_maintenance"  # being inspected / repaired (Phase 6)
    DAMAGED = "damaged"  # not fit for use, awaiting a decision
    RETIRED = "retired"  # permanently out of use (Slice 4.2)

    ALL = (AVAILABLE, ASSIGNED, UNDER_MAINTENANCE, DAMAGED, RETIRED)


ASSET_CODE_PREFIX = "AST-"
NAME_MAX_LENGTH = 200
SERIAL_MAX_LENGTH = 100
MODEL_MAX_LENGTH = 100
BRAND_MAX_LENGTH = 100
LOCATION_MAX_LENGTH = 200
RETIRE_REASON_MAX_LENGTH = 500  # A3

# The sequence behind AST-000001, AST-000002, ... (migration 0009). Owned by
# assets.asset_code, so it is dropped with the table.
asset_code_seq = Sequence("asset_code_seq", metadata=Base.metadata)


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'assigned', 'under_maintenance', 'damaged', 'retired')",
            name="status_valid",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("length(trim(serial_number)) > 0", name="serial_number_not_blank"),
        CheckConstraint("length(trim(model)) > 0", name="model_not_blank"),
        CheckConstraint("cost IS NULL OR cost >= 0", name="cost_not_negative"),
        CheckConstraint(
            "status = 'retired' OR (retired_at IS NULL AND retired_by_user_id IS NULL AND retire_reason IS NULL)",
            name="retired_details_only_when_retired",
        ),
    )
    # Read the database-made asset_code back right after the INSERT.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        server_default=text("'AST-' || lpad(nextval('asset_code_seq')::text, 6, '0')"),
    )
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("asset_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    brand: Mapped[str | None] = mapped_column(String(BRAND_MAX_LENGTH))
    model: Mapped[str] = mapped_column(String(MODEL_MAX_LENGTH), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(SERIAL_MAX_LENGTH), nullable=False)
    purchase_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_lines.id", ondelete="RESTRICT"), index=True
    )
    purchase_date: Mapped[date | None] = mapped_column(Date)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    warranty_expiry: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(LOCATION_MAX_LENGTH))
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AssetStatus.AVAILABLE, server_default=AssetStatus.AVAILABLE, index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Retirement (Slice 4.2): filled together, in the same transaction as the asset.retired audit row.
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    retire_reason: Mapped[str | None] = mapped_column(String(RETIRE_REASON_MAX_LENGTH))

    category: Mapped[AssetCategory] = relationship(lazy="joined")
    created_by: Mapped[User] = relationship(lazy="joined", foreign_keys=[created_by_user_id])
    retired_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[retired_by_user_id])
    purchase_line: Mapped["PurchaseLine | None"] = relationship(back_populates="assets")

    def __repr__(self) -> str:
        return f"<Asset {self.asset_code} {self.status}>"


# Serial numbers unique across ALL assets, ignoring case (AST-06, P5). Migration 0009.
Index("uq_assets_serial_number_lower", func.lower(Asset.serial_number), unique=True)
