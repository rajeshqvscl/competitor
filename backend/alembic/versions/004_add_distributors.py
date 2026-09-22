"""add distributors and company_distributors

Revision ID: 004
Revises: 003
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distributors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("territory", sa.String(200)),
        sa.Column("state", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("retailer_count", sa.Integer()),
        sa.Column("product_categories", sa.Text()),
        sa.Column("channel", sa.String(50)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("website", sa.String(500)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("confidence", sa.String(20), default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "company_distributors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("distributor_id", sa.Integer(), sa.ForeignKey("distributors.id"), nullable=False),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id")),
        sa.Column("is_primary", sa.Boolean(), default=False),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "distributor_id"),
    )


def downgrade() -> None:
    op.drop_table("company_distributors")
    op.drop_table("distributors")
