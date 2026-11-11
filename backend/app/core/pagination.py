"""Shared helper for paged lists. Every list endpoint uses it, so all lists behave the same.

Request (query string):   ?page=2&page_size=20&sort=-created_at
Response:                 {"items": [...], "total": 57, "page": 2, "page_size": 20}

- page       : which page, starting at 1
- page_size  : how many rows per page (1-100)
- sort       : a field name; a leading "-" means newest/largest first.
               Only fields the endpoint allows can be used (safe against tricks).
- filters    : each list endpoint adds its own query parameters (e.g. ?status=Available)
               and applies them to its query BEFORE calling paginate().

Example inside a service:

    stmt = select(Asset)
    if status_filter:
        stmt = stmt.where(Asset.status == status_filter)
    return paginate(db, stmt, params, sortable={"name": Asset.name, "created_at": Asset.created_at},
                    default_sort="-created_at")
"""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError

T = TypeVar("T")

MAX_PAGE_SIZE = 100


@dataclass
class PageParams:
    page: int
    page_size: int
    sort: str | None


def page_params(
    page: int = Query(1, ge=1, description="Page number, starting at 1."),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Rows per page (1-100)."),
    sort: str | None = Query(
        None,
        description='Field to sort by. Prefix with "-" for descending, e.g. "-created_at".',
        max_length=50,
    ),
) -> PageParams:
    """FastAPI dependency: use as  params: PageParams = Depends(page_params)."""
    return PageParams(page=page, page_size=page_size, sort=sort)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def paginate(
    db: Session,
    stmt: Select,
    params: PageParams,
    *,
    sortable: dict[str, Any],
    default_sort: str | None = None,
) -> dict[str, Any]:
    """Count all matching rows, then return one sorted page of them."""
    sort = params.sort or default_sort
    if sort:
        descending = sort.startswith("-")
        field = sort.lstrip("-")
        if field not in sortable:
            raise AppError(
                400,
                "invalid_sort",
                f'Cannot sort by "{field}".',
                {"allowed": sorted(sortable)},
            )
        column = sortable[field]
        stmt = stmt.order_by(column.desc() if descending else column.asc())

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(
        stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
    ).all()
    return {"items": list(items), "total": total, "page": params.page, "page_size": params.page_size}
