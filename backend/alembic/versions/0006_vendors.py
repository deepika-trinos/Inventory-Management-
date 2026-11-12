"""Vendors - Slice 2.3 (VEN-01 to VEN-03, VEN-05, BR-12).

- vendors: name (required), optional contact person, email, phone and address
  (VEN-02 "where available", decision B31), status, timestamps (UTC).
- name is unique ignoring upper/lower case, active or inactive (B30): unique
  index on lower(name), which also serves sorting and lookups by name.
- email is stored in lower case (B5) and may repeat across vendors (B31).
- status: 'active' or 'inactive'. Vendors are never deleted (BR-12, VEN-05).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("contact_person", sa.String(length=150), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive')", name=op.f("ck_vendors_status_valid")),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_vendors_email_lower_case")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vendors")),
    )
    op.create_index("uq_vendors_name_lower", "vendors", [sa.literal_column("lower(name)")], unique=True)
    op.create_index(op.f("ix_vendors_status"), "vendors", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_vendors_status"), table_name="vendors")
    op.drop_index("uq_vendors_name_lower", table_name="vendors")
    op.drop_table("vendors")
