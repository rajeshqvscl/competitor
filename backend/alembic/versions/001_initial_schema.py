"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ownership_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.Text()),
    )

    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("regions.id")),
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), unique=True, nullable=False),
        sa.Column("ownership_type_id", sa.Integer(), sa.ForeignKey("ownership_types.id")),
        sa.Column("parent_company", sa.String(200)),
        sa.Column("website", sa.String(500)),
        sa.Column("headquarters_region_id", sa.Integer(), sa.ForeignKey("regions.id")),
        sa.Column("origin_region_id", sa.Integer(), sa.ForeignKey("regions.id")),
        sa.Column("is_listed", sa.Boolean(), default=False),
        sa.Column("is_global", sa.Boolean(), default=False),
        sa.Column("description", sa.Text()),
        sa.Column("source_url", sa.String(500)),
        sa.Column("source_date", sa.Date()),
        sa.Column("confidence", sa.String(20), default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "name"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text()),
    )

    op.create_table(
        "subcategories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("category_id", "name"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("subcategory_id", sa.Integer(), sa.ForeignKey("subcategories.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("brand_id", "subcategory_id", "name"),
    )

    op.create_table(
        "skus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("variant", sa.String(100)),
        sa.Column("pack_size", sa.Numeric(10, 2)),
        sa.Column("unit", sa.String(20)),
        sa.Column("packaging_type", sa.String(50)),
        sa.Column("mrp", sa.Numeric(10, 2)),
        sa.Column("selling_price", sa.Numeric(10, 2)),
        sa.Column("fat_percent", sa.Numeric(5, 2)),
        sa.Column("protein_percent", sa.Numeric(5, 2)),
        sa.Column("shelf_life_days", sa.Integer()),
        sa.Column("storage_requirement", sa.String(50)),
        sa.Column("flavour", sa.String(100)),
        sa.Column("target_segment", sa.String(100)),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("source_url", sa.String(500)),
        sa.Column("source_date", sa.Date()),
        sa.Column("last_verified", sa.Date()),
        sa.Column("confidence", sa.String(20), default="medium"),
        sa.Column("canonical_sku_id", sa.Integer(), sa.ForeignKey("skus.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "retailers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("parent_company", sa.String(200)),
        sa.Column("website", sa.String(500)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sku_retailers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("retailer_id", sa.Integer(), sa.ForeignKey("retailers.id"), nullable=False),
        sa.Column("region_id", sa.Integer(), sa.ForeignKey("regions.id")),
        sa.Column("channel", sa.String(50)),
        sa.Column("available", sa.Boolean(), default=True),
        sa.Column("source_url", sa.String(500)),
        sa.Column("source_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("sku_id", "retailer_id", "region_id"),
    )

    op.create_table(
        "company_regions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("region_id", sa.Integer(), sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), default=False),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "region_id"),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(50)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("extracted_fact", sa.Text()),
        sa.Column("extraction_date", sa.Date()),
        sa.Column("last_verified", sa.Date()),
        sa.Column("confidence", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sources")
    op.drop_table("company_regions")
    op.drop_table("sku_retailers")
    op.drop_table("retailers")
    op.drop_table("skus")
    op.drop_table("products")
    op.drop_table("subcategories")
    op.drop_table("categories")
    op.drop_table("brands")
    op.drop_table("companies")
    op.drop_table("regions")
    op.drop_table("ownership_types")
