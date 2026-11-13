"""Assets - Slice 3.2 (AST-01, AST-02, AST-06, BR-01, BR-08, PUR-06).

- assets: system ID AST-000001... (sequence asset_code_seq, Q3, BR-01), name,
  category, brand (optional), model (required), serial number (required), the
  purchase line it was received on, purchase date and cost (from the line),
  warranty expiry and location (optional, location typed, Q1), status
  (available / assigned / under_maintenance / damaged / retired, PRD 8.1; new
  assets start as available), created-by user, timestamps (UTC).
- Serial numbers unique across all assets ignoring case (AST-06, P5): unique
  index on lower(serial_number).
- purchase_line_id, purchase_date and cost are empty for equipment entered by
  hand (Slice 4.5).
- All foreign keys are ON DELETE RESTRICT: assets are never deleted (BR-12).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("asset_code_seq")))
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "asset_code",
            sa.String(length=20),
            server_default=sa.text("'AST-' || lpad(nextval('asset_code_seq')::text, 6, '0')"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=False),
        sa.Column("purchase_line_id", sa.Integer(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("warranty_expiry", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="available", nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('available', 'assigned', 'under_maintenance', 'damaged', 'retired')",
            name=op.f("ck_assets_status_valid"),
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_assets_name_not_blank")),
        sa.CheckConstraint("length(trim(serial_number)) > 0", name=op.f("ck_assets_serial_number_not_blank")),
        sa.CheckConstraint("length(trim(model)) > 0", name=op.f("ck_assets_model_not_blank")),
        sa.CheckConstraint("cost IS NULL OR cost >= 0", name=op.f("ck_assets_cost_not_negative")),
        sa.ForeignKeyConstraint(
            ["category_id"], ["asset_categories.id"],
            name=op.f("fk_assets_category_id_asset_categories"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_line_id"], ["purchase_lines.id"],
            name=op.f("fk_assets_purchase_line_id_purchase_lines"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name=op.f("fk_assets_created_by_user_id_users"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
        sa.UniqueConstraint("asset_code", name=op.f("uq_assets_asset_code")),
    )
    # The sequence belongs to the column: dropped with the table, and reset by
    # TRUNCATE ... RESTART IDENTITY (used by the tests).
    op.execute("ALTER SEQUENCE asset_code_seq OWNED BY assets.asset_code")
    op.create_index(op.f("ix_assets_category_id"), "assets", ["category_id"])
    op.create_index(op.f("ix_assets_purchase_line_id"), "assets", ["purchase_line_id"])
    op.create_index(op.f("ix_assets_status"), "assets", ["status"])
    op.create_index(op.f("ix_assets_created_by_user_id"), "assets", ["created_by_user_id"])
    op.create_index(
        "uq_assets_serial_number_lower",
        "assets",
        [sa.literal_column("lower(serial_number)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_assets_serial_number_lower", table_name="assets")
    op.drop_index(op.f("ix_assets_created_by_user_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_status"), table_name="assets")
    op.drop_index(op.f("ix_assets_purchase_line_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_category_id"), table_name="assets")
    op.drop_table("assets")  # also drops asset_code_seq (OWNED BY)
    op.execute("DROP SEQUENCE IF EXISTS asset_code_seq")
