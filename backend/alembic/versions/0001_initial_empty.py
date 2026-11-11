"""Initial empty migration (Slice 1.2).

Creates no tables. Running it proves Alembic can reach the database; Alembic
also creates its own small "alembic_version" table to remember which
migrations have been applied. Real tables start in Slice 1.3.

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
