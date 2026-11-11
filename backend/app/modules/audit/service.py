"""The one audit helper every slice uses: record().

HOW TO USE (inside a service function that changes something):

    before = audit.snapshot(user, ["role"])
    user.role = new_role
    audit.record(db, actor=admin, action=AuditAction.USER_ROLE_CHANGED,
                 entity=user, before=before, after=audit.snapshot(user, ["role"]))
    db.commit()        # <- saves the change AND the audit row together

SAME TRANSACTION: record() only ADDS the audit row to the session you pass in;
it never commits. A "transaction" is a group of database changes that are saved
all together or not at all. So:
  - if the business change is rolled back, its audit row disappears with it;
  - if the audit row cannot be saved, the business change is rolled back too.
You can never get a change without its audit row, or an audit row for a
change that did not happen.

SECRETS: record() removes passwords, password hashes, tokens and secrets from
before/after data automatically, at any depth.
"""

import ipaddress
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.modules.audit.actions import AuditAction
from app.modules.audit.models import AuditLog
from app.modules.users.models import User

# ---- Removing secrets ----------------------------------------------------------
_SECRET_KEYS = {
    "password",
    "password_hash",
    "new_password",
    "old_password",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "secret",
    "api_key",
    "authorization",
}


def _is_secret_key(key: str) -> bool:
    k = key.lower()
    return k in _SECRET_KEYS or "password" in k or "secret" in k or k.endswith("_token")


def _json_safe(value: Any) -> Any:
    """Make a value storable as JSON, dropping secret keys on the way."""
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items() if not _is_secret_key(str(k))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def sanitize(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Copy of `data` without secrets, ready to store as JSON."""
    if data is None:
        return None
    return _json_safe(data)


def snapshot(obj: Any, fields: Iterable[str]) -> dict[str, Any]:
    """Take a before/after picture of selected fields of a database object.

    A related object (e.g. user.role) is stored by its name or id, so the
    audit row stays readable even if that record changes later.
    """
    result: dict[str, Any] = {}
    for field in fields:
        value = getattr(obj, field)
        if hasattr(value, "__table__"):  # a related record
            value = getattr(value, "name", None) or getattr(value, "id", None)
        result[field] = value
    return result


# ---- Where the request came from (optional) -------------------------------------
@dataclass(frozen=True)
class AuditContext:
    ip_address: str | None = None
    request_id: str | None = None


def get_audit_context(request: Request) -> AuditContext:
    """FastAPI dependency: the caller's IP address and X-Request-ID header, if any."""
    ip = request.client.host if request.client else None
    try:
        ip = str(ipaddress.ip_address(ip)) if ip else None
    except ValueError:  # e.g. the test client reports "testclient"
        ip = None
    request_id = (request.headers.get("X-Request-ID") or "")[:64] or None
    return AuditContext(ip_address=ip, request_id=request_id)


# ---- The helper ---------------------------------------------------------------------
def record(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity: Any = None,
    entity_type: str | None = None,
    entity_id: Any = None,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    context: AuditContext | None = None,
) -> AuditLog:
    """Add one audit row to the CURRENT transaction (does not commit).

    actor   : the logged-in user who did it, or None for a system action
    action  : one of AuditAction (e.g. AuditAction.USER_ROLE_CHANGED)
    entity  : the changed database object (its table name and id are used), OR
              give entity_type + entity_id yourself
    before / after : what changed (secrets are removed automatically)
    """
    if action not in AuditAction.all():
        raise ValueError(f"Unknown audit action {action!r}. Add it to AuditAction first.")

    if entity is not None:
        if entity.id is None:  # new object: get its id from the database first
            db.flush()
        entity_type = entity.__tablename__
        entity_id = entity.id
    if not entity_type or entity_id is None:
        raise ValueError("audit.record needs an entity, or entity_type and entity_id.")

    context = context or AuditContext()
    entry = AuditLog(
        actor_user_id=actor.id if actor is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_data=sanitize(before),
        after_data=sanitize(after),
        ip_address=context.ip_address,
        request_id=context.request_id,
    )
    db.add(entry)
    db.flush()  # send it now so any problem (e.g. bad actor id) fails here, inside the transaction
    return entry


# ---- Append-only guard in the application ---------------------------------------
@event.listens_for(Session, "before_flush")
def _block_audit_changes(session: Session, _flush_context: Any, _instances: Any) -> None:
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise PermissionError("Audit log rows can never be deleted.")
    for obj in session.dirty:
        if isinstance(obj, AuditLog) and session.is_modified(obj):
            raise PermissionError("Audit log rows can never be changed.")
