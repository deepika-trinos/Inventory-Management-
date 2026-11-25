"""Maintenance requests - Slice 6.1 (MNT-01 to MNT-03; owner's answers Q9, Q10, O1-O14; decision M1).

- maintenance_requests: one row per reported problem with an asset: system number
  MNT-000001... (sequence maintenance_request_number_seq, O11), asset, issue description
  (up to 1,000, not blank, O4), optional priority low / medium / high (Q10), status
  reported / in_progress / completed / cancelled (MNT-04; 6.1 writes only "reported"),
  reported date (business date), who reported it, when it was saved.
- uq_maintenance_requests_open_asset: a PARTIAL unique index, so an asset can have only
  ONE open (Reported or In Progress) request, even if two people report at the same moment (O2).
- Repair notes, provider, cost and completion date are added by Slice 6.2.
- A new table only: no existing row is changed.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("maintenance_request_number_seq")))
    op.create_table(
        "maintenance_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "request_number",
            sa.String(length=20),
            server_default=sa.text("'MNT-' || lpad(nextval('maintenance_request_number_seq')::text, 6, '0')"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("issue_description", sa.String(length=1000), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="reported", nullable=False),
        sa.Column("reported_date", sa.Date(), nullable=False),
        sa.Column("reported_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('reported', 'in_progress', 'completed', 'cancelled')",
            name=op.f("ck_maintenance_requests_status_valid"),
        ),
        sa.CheckConstraint(
            "priority IS NULL OR priority IN ('low', 'medium', 'high')",
            name=op.f("ck_maintenance_requests_priority_valid"),
        ),
        sa.CheckConstraint(
            "length(trim(issue_description)) > 0", name=op.f("ck_maintenance_requests_issue_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_maintenance_requests_asset_id_assets"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reported_by_user_id"], ["users.id"], name=op.f("fk_maintenance_requests_reported_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_maintenance_requests")),
        sa.UniqueConstraint("request_number", name=op.f("uq_maintenance_requests_request_number")),
    )
    # The sequence belongs to the column: dropped with the table, and reset by
    # TRUNCATE ... RESTART IDENTITY in the tests.
    op.execute("ALTER SEQUENCE maintenance_request_number_seq OWNED BY maintenance_requests.request_number")
    op.create_index(op.f("ix_maintenance_requests_asset_id"), "maintenance_requests", ["asset_id"])
    op.create_index(op.f("ix_maintenance_requests_status"), "maintenance_requests", ["status"])
    op.create_index(
        op.f("ix_maintenance_requests_reported_by_user_id"), "maintenance_requests", ["reported_by_user_id"]
    )
    op.create_index(
        "uq_maintenance_requests_open_asset", "maintenance_requests", ["asset_id"], unique=True,
        postgresql_where=sa.text("status IN ('reported', 'in_progress')"),
    )


def downgrade() -> None:
    op.drop_index("uq_maintenance_requests_open_asset", table_name="maintenance_requests")
    op.drop_index(op.f("ix_maintenance_requests_reported_by_user_id"), table_name="maintenance_requests")
    op.drop_index(op.f("ix_maintenance_requests_status"), table_name="maintenance_requests")
    op.drop_index(op.f("ix_maintenance_requests_asset_id"), table_name="maintenance_requests")
    op.drop_table("maintenance_requests")  # also drops maintenance_request_number_seq (OWNED BY)
    op.execute("DROP SEQUENCE IF EXISTS maintenance_request_number_seq")
