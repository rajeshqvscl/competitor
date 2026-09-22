"""add price history, change events, saved analyses

Revision ID: 002
Revises: 001
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("mrp", sa.Numeric(10, 2)),
        sa.Column("selling_price", sa.Numeric(10, 2)),
        sa.Column("discount_percent", sa.Numeric(5, 2)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "change_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("field_name", sa.String(100)),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("source_url", sa.String(500)),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "saved_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("filters", sa.Text()),
        sa.Column("results", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("saved_analyses")
    op.drop_table("change_events")
    op.drop_table("price_history")
