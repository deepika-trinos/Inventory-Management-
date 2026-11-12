"""The asset_categories table (Slice 2.1, AST-02, PRD 9.2).

- Each category is either tracked ONE BY ONE ("serialized", e.g. laptops:
  every unit becomes its own asset record) or BY QUANTITY ("bulk", e.g. mice:
  a stock balance). PRD 9.2: the same physical units must never be counted in
  both models, so the category decides which model its items use.
- Name is unique ignoring upper/lower case: "Laptops" and "LAPTOPS" count as
  the same name (unique index on lower(name)), whether active or inactive.
- Never deleted, only deactivated (BR-12, decisions.md gap 2).
"""

from sqlalchemy import CheckConstraint, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class TrackingType:
    """How items of a category are tracked. Use these, never typed strings."""

    SERIALIZED = "serialized"  # one by one: each unit is an asset with its own ID
    BULK = "bulk"  # by quantity: a stock balance

    ALL = (SERIALIZED, BULK)


class CategoryStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"

    ALL = (ACTIVE, INACTIVE)


NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 500


class AssetCategory(TimestampMixin, Base):
    __tablename__ = "asset_categories"
    __table_args__ = (
        CheckConstraint("tracking_type IN ('serialized', 'bulk')", name="tracking_type_valid"),
        CheckConstraint("status IN ('active', 'inactive')", name="status_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), nullable=False)
    description: Mapped[str | None] = mapped_column(String(DESCRIPTION_MAX_LENGTH))
    tracking_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CategoryStatus.ACTIVE, server_default=CategoryStatus.ACTIVE
    )

    @property
    def is_active(self) -> bool:
        return self.status == CategoryStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<AssetCategory {self.id} {self.name}>"


# Case-insensitive uniqueness: a unique index on lower(name).
Index("uq_asset_categories_name_lower", func.lower(AssetCategory.name), unique=True)
