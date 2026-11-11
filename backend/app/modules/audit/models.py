"""The audit_logs table.

APPEND-ONLY: rows are only ever added. Three layers make sure of that:
1. There is no update/delete endpoint or service function.
2. The ORM refuses to flush a change or delete of an AuditLog row (see service.py).
3. A database trigger rejects UPDATE and DELETE on audit_logs (migration 0003),
   so even hand-written SQL cannot alter history.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Who did it. Empty (NULL) for actions done by the system itself.
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "user.role_changed"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "users"
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "42"
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Database time at the start of the transaction, in UTC.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(INET)
    request_id: Mapped[str | None] = mapped_column(String(64))

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} {self.action} {self.entity_type}:{self.entity_id}>"
