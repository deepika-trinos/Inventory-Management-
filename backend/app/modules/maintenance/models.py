"""The maintenance_requests table: a reported problem with an asset (Slice 6.1: MNT-01 to MNT-03;
owner's answers Q9, Q10, O1-O14; decisions M1-M8 in decisions.md section 32).

- request_number: made by the system, MNT-000001, MNT-000002, ... (O11), from the database
  sequence maintenance_request_number_seq. Read-only.
- issue_description: required, up to 1,000 characters (O4).
- priority: optional Low / Medium / High, set by the IT Manager only (Q10, O8).
- status (MNT-04): reported, in_progress, completed, cancelled. Slice 6.1 only creates
  REPORTED requests; Slice 6.2 moves them on.
- reported_date: the business date (O5); reported_by_user_id: who reported it (O9);
  created_at: when it was saved (UTC).
- OPEN request = Reported or In Progress. An asset has at most ONE open request (O2):
  enforced by the partial unique index uq_maintenance_requests_open_asset (migration 0015),
  in addition to the asset row lock.
- Reporting never changes the asset's status (Q9): it becomes Under Maintenance only when
  work starts (Slice 6.2).
- Never deleted (BR-12).
"""

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Sequence, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.assets.models import Asset
from app.modules.users.models import User

ISSUE_MAX_LENGTH = 1000  # O4
REQUEST_NUMBER_PREFIX = "MNT-"


class MaintenanceStatus:
    """MNT-04. Stored in lower case; the screen shows "In Progress" etc."""

    REPORTED = "reported"
    IN_PROGRESS = "in_progress"  # Slice 6.2
    COMPLETED = "completed"  # Slice 6.2
    CANCELLED = "cancelled"  # Slice 6.2

    ALL = (REPORTED, IN_PROGRESS, COMPLETED, CANCELLED)
    OPEN = (REPORTED, IN_PROGRESS)  # O2


class MaintenancePriority:
    """Q10: optional, set by the IT Manager."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    ALL = (LOW, MEDIUM, HIGH)


# The sequence behind MNT-000001, MNT-000002, ... (migration 0015). Owned by
# maintenance_requests.request_number, so it is dropped with the table.
maintenance_request_number_seq = Sequence("maintenance_request_number_seq", metadata=Base.metadata)


class MaintenanceRequest(TimestampMixin, Base):
    __tablename__ = "maintenance_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reported', 'in_progress', 'completed', 'cancelled')", name="status_valid"
        ),
        CheckConstraint("priority IS NULL OR priority IN ('low', 'medium', 'high')", name="priority_valid"),
        CheckConstraint("length(trim(issue_description)) > 0", name="issue_not_blank"),
    )
    # Read the database-made request_number back right after the INSERT.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    request_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        server_default=text("'MNT-' || lpad(nextval('maintenance_request_number_seq')::text, 6, '0')"),
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)
    issue_description: Mapped[str] = mapped_column(String(ISSUE_MAX_LENGTH), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MaintenanceStatus.REPORTED, server_default=MaintenanceStatus.REPORTED,
        index=True,
    )
    reported_date: Mapped[date] = mapped_column(Date, nullable=False)
    reported_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    asset: Mapped[Asset] = relationship(lazy="joined")
    reported_by: Mapped[User] = relationship(lazy="joined", foreign_keys=[reported_by_user_id])

    @property
    def is_open(self) -> bool:
        return self.status in MaintenanceStatus.OPEN

    def __repr__(self) -> str:
        return f"<MaintenanceRequest {self.request_number} {self.status}>"


# At most ONE open (Reported or In Progress) request per asset (O2). Migration 0015.
Index(
    "uq_maintenance_requests_open_asset",
    MaintenanceRequest.asset_id,
    unique=True,
    postgresql_where=text("status IN ('reported', 'in_progress')"),
)
