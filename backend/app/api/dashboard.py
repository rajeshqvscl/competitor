from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models import (
    Company, Brand, Product, Sku, Retailer, Region,
    CompanyRegion, OwnershipType, Category, Subcategory
)

router = APIRouter()


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    total_companies = db.query(Company).count()
    total_brands = db.query(Brand).count()
    total_products = db.query(Product).count()
    total_skus = db.query(Sku).count()
    total_retailers = db.query(Retailer).count()
    total_regions = db.query(Region).filter(Region.level == "region").count()

    # Companies by ownership
    ownership_rows = (
        db.query(OwnershipType.name, func.count(Company.id))
        .join(Company, Company.ownership_type_id == OwnershipType.id)
        .group_by(OwnershipType.name)
        .all()
    )
    companies_by_ownership = {name: count for name, count in ownership_rows}

    # Companies by region (primary)
    region_rows = (
        db.query(Region.name, func.count(Company.id))
        .join(CompanyRegion, CompanyRegion.region_id == Region.id)
        .join(Company, Company.id == CompanyRegion.company_id)
        .filter(Region.level == "region")
        .group_by(Region.name)
        .all()
    )
    companies_by_region = {name: count for name, count in region_rows}

    # SKUs by category
    sku_cat_rows = (
        db.query(Category.name, func.count(Sku.id))
        .join(Subcategory, Subcategory.category_id == Category.id)
        .join(Product, Product.subcategory_id == Subcategory.id)
        .join(Sku, Sku.product_id == Product.id)
        .group_by(Category.name)
        .all()
    )
    skus_by_category = {name: count for name, count in sku_cat_rows}

    return {
        "total_companies": total_companies,
        "total_brands": total_brands,
        "total_products": total_products,
        "total_skus": total_skus,
        "total_retailers": total_retailers,
        "total_regions": total_regions,
        "companies_by_ownership": companies_by_ownership,
        "companies_by_region": companies_by_region,
        "skus_by_category": skus_by_category,
    }
