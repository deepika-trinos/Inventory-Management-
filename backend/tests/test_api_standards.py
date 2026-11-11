"""Shared API standards: error format and the paged-list helper (Slice 1.3)."""

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.modules.users.models import Role

ROLE_SORTS = {"name": Role.name, "id": Role.id}


def test_unknown_address_uses_standard_error_format(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Not Found", "details": None}
    }


def test_paginate_returns_items_total_page_and_page_size(db):
    page = paginate(db, select(Role), PageParams(page=1, page_size=2, sort="name"), sortable=ROLE_SORTS)

    assert page["total"] == 3
    assert page["page"] == 1
    assert page["page_size"] == 2
    assert [r.name for r in page["items"]] == ["Admin", "Employee"]


def test_paginate_second_page_and_descending_sort(db):
    page = paginate(db, select(Role), PageParams(page=2, page_size=2, sort="-name"), sortable=ROLE_SORTS)

    assert [r.name for r in page["items"]] == ["Admin"]
    assert page["total"] == 3


def test_paginate_applies_filters_before_counting(db):
    stmt = select(Role).where(Role.name != "Admin")

    page = paginate(db, stmt, PageParams(page=1, page_size=20, sort=None), sortable=ROLE_SORTS, default_sort="id")

    assert page["total"] == 2
    assert [r.name for r in page["items"]] == ["IT Manager", "Employee"]


def test_paginate_refuses_sorting_by_unlisted_field(db):
    with pytest.raises(AppError) as exc:
        paginate(db, select(Role), PageParams(page=1, page_size=20, sort="description"), sortable=ROLE_SORTS)

    assert exc.value.status_code == 400
    assert exc.value.code == "invalid_sort"
    assert exc.value.details == {"allowed": ["id", "name"]}
