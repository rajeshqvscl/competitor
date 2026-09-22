"""add alerts, alert notifications, review queue

Revision ID: 003
Revises: 002
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id")),
        sa.Column("region_id", sa.Integer(), sa.ForeignKey("regions.id")),
        sa.Column("event_types", sa.Text()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_checked", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alert_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=False),
        sa.Column("change_event_id", sa.Integer(), sa.ForeignKey("change_events.id")),
        sa.Column("message", sa.Text()),
        sa.Column("is_read", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "review_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("data", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("reviewed_by", sa.String(100)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("review_queue")
    op.drop_table("alert_notifications")
    op.drop_table("alerts")
