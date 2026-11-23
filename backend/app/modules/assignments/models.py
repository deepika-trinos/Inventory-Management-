"""The assignments table: which employee holds which asset (Slice 5.1, ASN-01 to ASN-04, BR-02, BR-03, BR-05, BR-11).

- One row per time an asset is given to an employee. Old rows are kept, never
  overwritten (ASN-07): returning (Slice 5.2) fills the return fields of the row.
- OPEN assignment = not returned yet (returned_at empty). An asset has at most ONE
  open assignment: enforced by the partial unique index uq_assignments_open_asset
  (migration 0014), in addition to the row lock and the Available-only check.
- assignment_date: the business date (owner's answer N1): today by default, earlier
  allowed, never in the future, never before the asset was created.
- expected_return_date: optional; on or after the assignment date (N2; check
  constraint). Not editable later in v1.
- assigned_by_user_id: who assigned it; created_at: when it was saved (UTC).
- Return fields (return_date, return_outcome, condition_notes, returned_at,
  returned_by_user_id) are left empty in 5.1 and filled by Slice 5.2 (owner's answer
  N4). A check constraint keeps the required ones filled together.
- Never deleted (BR-12).
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.assets.models import Asset
from app.modules.employees.models import Employee
from app.modules.users.models import User

CONDITION_NOTES_MAX_LENGTH = 1000  # N4 (Slice 5.2)


class ReturnOutcome:
    """Inspection outcome on return (N4, Slice 5.2): the asset's next status."""

    AVAILABLE = "available"
    UNDER_MAINTENANCE = "under_maintenance"
    DAMAGED = "damaged"

    ALL = (AVAILABLE, UNDER_MAINTENANCE, DAMAGED)


class Assignment(TimestampMixin, Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint(
            "expected_return_date IS NULL OR expected_return_date >= assignment_date",
            name="expected_return_not_before_assignment",
        ),
        CheckConstraint(
            "(returned_at IS NULL AND return_date IS NULL AND return_outcome IS NULL"
            " AND returned_by_user_id IS NULL AND condition_notes IS NULL)"
            " OR (returned_at IS NOT NULL AND return_date IS NOT NULL AND return_outcome IS NOT NULL"
            " AND returned_by_user_id IS NOT NULL)",
            name="return_details_together",
        ),
        CheckConstraint("return_date IS NULL OR return_date >= assignment_date", name="return_not_before_assignment"),
        CheckConstraint(
            "return_outcome IS NULL OR return_outcome IN ('available', 'under_maintenance', 'damaged')",
            name="return_outcome_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assignment_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_return_date: Mapped[date | None] = mapped_column(Date)
    assigned_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Return (Slice 5.2, N4): empty while the assignment is open.
    return_date: Mapped[date | None] = mapped_column(Date)
    return_outcome: Mapped[str | None] = mapped_column(String(30))
    condition_notes: Mapped[str | None] = mapped_column(String(CONDITION_NOTES_MAX_LENGTH))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)

    asset: Mapped[Asset] = relationship(lazy="joined")
    employee: Mapped[Employee] = relationship(lazy="joined")
    assigned_by: Mapped[User] = relationship(lazy="joined", foreign_keys=[assigned_by_user_id])
    returned_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[returned_by_user_id])

    @property
    def is_open(self) -> bool:
        return self.returned_at is None

    def __repr__(self) -> str:
        return f"<Assignment {self.id} asset={self.asset_id} employee={self.employee_id}>"


# At most ONE open (not returned) assignment per asset (BR-02, BR-03). Migration 0014.
Index(
    "uq_assignments_open_asset",
    Assignment.asset_id,
    unique=True,
    postgresql_where=text("returned_at IS NULL"),
)
