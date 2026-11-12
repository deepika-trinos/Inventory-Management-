"""The vendors table (Slice 2.3, VEN-01 to VEN-03, VEN-05).

- Only the name is required; contact person, email, phone and address are
  stored "where available" (VEN-02, decision B31).
- Name is unique ignoring upper/lower case, active or inactive (B30).
- Email is stored in lower case (B5) and may repeat across vendors (B31).
- Never deleted, only deactivated (BR-12, VEN-05). Purchases may only be
  created from an ACTIVE vendor (Slice 3.1, see service.ensure_vendor_active).
"""

from sqlalchemy import CheckConstraint, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class VendorStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"

    ALL = (ACTIVE, INACTIVE)


NAME_MAX_LENGTH = 150
CONTACT_PERSON_MAX_LENGTH = 150
EMAIL_MAX_LENGTH = 255
PHONE_MAX_LENGTH = 30
ADDRESS_MAX_LENGTH = 500


class Vendor(TimestampMixin, Base):
    __tablename__ = "vendors"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="status_valid"),
        CheckConstraint("email = lower(email)", name="email_lower_case"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(CONTACT_PERSON_MAX_LENGTH))
    email: Mapped[str | None] = mapped_column(String(EMAIL_MAX_LENGTH))
    phone: Mapped[str | None] = mapped_column(String(PHONE_MAX_LENGTH))
    address: Mapped[str | None] = mapped_column(String(ADDRESS_MAX_LENGTH))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=VendorStatus.ACTIVE, server_default=VendorStatus.ACTIVE, index=True
    )

    @property
    def is_active(self) -> bool:
        return self.status == VendorStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<Vendor {self.id} {self.name}>"


# Case-insensitive uniqueness: a unique index on lower(name) (migration 0006).
Index("uq_vendors_name_lower", func.lower(Vendor.name), unique=True)
