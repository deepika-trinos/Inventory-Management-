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

Slice 6.2 (MNT-04 to MNT-07; owner's answers S1-S14; decisions U1-U9 in decisions.md section 34),
migration 0016:
- Start work (Reported -> In Progress): started_date (business date), started_at, started_by_user_id.
  The asset becomes Under Maintenance (Q9).
- Details: service_provider (company or person, up to 200), repair_notes (up to 1,000), cost (INR,
  NUMERIC(12,2), 0 or more). Editable while the request is open.
- Completed: completion_date, completed_at, completed_by_user_id (repair notes required).
- Cancelled: cancelled_at, cancelled_by_user_id, cancel_reason (up to 500).
- Completed and Cancelled are final (S4). Check constraints keep each group consistent with the status.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, Sequence, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.assets.models import Asset
from app.modules.users.models import User

ISSUE_MAX_LENGTH = 1000  # O4
SERVICE_PROVIDER_MAX_LENGTH = 200  # S9
REPAIR_NOTES_MAX_LENGTH = 1000  # S12
CANCEL_REASON_MAX_LENGTH = 500  # S11

# Slice 6.2 check constraints (migration 0016), in one place for the model and the migration.
STARTED_TOGETHER = (
    "(started_date IS NULL AND started_at IS NULL AND started_by_user_id IS NULL)"
    " OR (started_date IS NOT NULL AND started_at IS NOT NULL AND started_by_user_id IS NOT NULL)"
)
STARTED_MATCHES_STATUS = (
    "(status = 'reported' AND started_at IS NULL)"
    " OR (status IN ('in_progress', 'completed') AND started_at IS NOT NULL)"
    " OR status = 'cancelled'"
)
COMPLETED_MATCHES_STATUS = (
    "(status = 'completed' AND completion_date IS NOT NULL AND completed_at IS NOT NULL"
    " AND completed_by_user_id IS NOT NULL AND repair_notes IS NOT NULL)"
    " OR (status <> 'completed' AND completion_date IS NULL AND completed_at IS NULL"
    " AND completed_by_user_id IS NULL)"
)
CANCELLED_MATCHES_STATUS = (
    "(status = 'cancelled' AND cancelled_at IS NOT NULL AND cancelled_by_user_id IS NOT NULL"
    " AND cancel_reason IS NOT NULL)"
    " OR (status <> 'cancelled' AND cancelled_at IS NULL AND cancelled_by_user_id IS NULL AND cancel_reason IS NULL)"
)
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
        # Slice 6.2 (migration 0016, U1)
        CheckConstraint(STARTED_TOGETHER, name="started_together"),
        CheckConstraint(STARTED_MATCHES_STATUS, name="started_matches_status"),
        CheckConstraint(COMPLETED_MATCHES_STATUS, name="completed_matches_status"),
        CheckConstraint(CANCELLED_MATCHES_STATUS, name="cancelled_matches_status"),
        CheckConstraint("cost IS NULL OR cost >= 0", name="cost_not_negative"),
        CheckConstraint("started_date IS NULL OR started_date >= reported_date", name="started_not_before_reported"),
        CheckConstraint(
            "completion_date IS NULL OR completion_date >= started_date", name="completion_not_before_start"
        ),
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
    # Slice 6.2 (U1): start, details, completion, cancellation.
    started_date: Mapped[date | None] = mapped_column(Date)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    service_provider: Mapped[str | None] = mapped_column(String(SERVICE_PROVIDER_MAX_LENGTH))
    repair_notes: Mapped[str | None] = mapped_column(String(REPAIR_NOTES_MAX_LENGTH))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    completion_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancel_reason: Mapped[str | None] = mapped_column(String(CANCEL_REASON_MAX_LENGTH))

    asset: Mapped[Asset] = relationship(lazy="joined")
    reported_by: Mapped[User] = relationship(lazy="joined", foreign_keys=[reported_by_user_id])
    started_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[started_by_user_id])
    completed_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[completed_by_user_id])
    cancelled_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[cancelled_by_user_id])

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
