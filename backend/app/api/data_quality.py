from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models import (
    Company, Brand, Product, Sku, Retailer, Category, Subcategory,
    SkuRetailer, CompanyRegion, Source
)

router = APIRouter()


@router.get("")
def data_quality_dashboard(db: Session = Depends(get_db)):
    total_companies = db.query(Company).count()
    total_brands = db.query(Brand).count()
    total_products = db.query(Product).count()
    total_skus = db.query(Sku).count()
    total_retailers = db.query(Retailer).count()

    # Completeness checks
    skus_with_mrp = db.query(Sku).filter(Sku.mrp.isnot(None)).count()
    skus_with_price = db.query(Sku).filter(Sku.selling_price.isnot(None)).count()
    skus_with_fat = db.query(Sku).filter(Sku.fat_percent.isnot(None)).count()
    skus_with_source = db.query(Sku).filter(Sku.source_url.isnot(None)).count()
    companies_with_website = db.query(Company).filter(Company.website.isnot(None)).count()
    companies_with_desc = db.query(Company).filter(Company.description.isnot(None)).count()

    # Coverage
    skus_with_retailer = db.query(SkuRetailer.sku_id.distinct()).count()
    companies_with_region = db.query(CompanyRegion.company_id.distinct()).count()

    # Sources
    total_sources = db.query(Source).count()
    high_confidence = db.query(Source).filter(Source.confidence == "high").count()
    medium_confidence = db.query(Source).filter(Source.confidence == "medium").count()
    low_confidence = db.query(Source).filter(Source.confidence == "low").count()

    # Category coverage
    cats_with_products = db.query(Category.id).join(Subcategory).join(Product).distinct().count()
    total_cats = db.query(Category).count()

    subcats_with_products = db.query(Subcategory.id).join(Product).distinct().count()
    total_subcats = db.query(Subcategory).count()

    return {
        "overview": {
            "companies": total_companies,
            "brands": total_brands,
            "products": total_products,
            "skus": total_skus,
            "retailers": total_retailers,
        },
        "completeness": {
            "sku_mrp": {"count": skus_with_mrp, "total": total_skus, "percent": round(skus_with_mrp / total_skus * 100, 1) if total_skus else 0},
            "sku_price": {"count": skus_with_price, "total": total_skus, "percent": round(skus_with_price / total_skus * 100, 1) if total_skus else 0},
            "sku_fat": {"count": skus_with_fat, "total": total_skus, "percent": round(skus_with_fat / total_skus * 100, 1) if total_skus else 0},
            "sku_source": {"count": skus_with_source, "total": total_skus, "percent": round(skus_with_source / total_skus * 100, 1) if total_skus else 0},
            "company_website": {"count": companies_with_website, "total": total_companies, "percent": round(companies_with_website / total_companies * 100, 1) if total_companies else 0},
            "company_description": {"count": companies_with_desc, "total": total_companies, "percent": round(companies_with_desc / total_companies * 100, 1) if total_companies else 0},
        },
        "coverage": {
            "skus_at_retailer": {"count": skus_with_retailer, "total": total_skus, "percent": round(skus_with_retailer / total_skus * 100, 1) if total_skus else 0},
            "companies_in_region": {"count": companies_with_region, "total": total_companies, "percent": round(companies_with_region / total_companies * 100, 1) if total_companies else 0},
            "categories_with_products": {"count": cats_with_products, "total": total_cats, "percent": round(cats_with_products / total_cats * 100, 1) if total_cats else 0},
            "subcategories_with_products": {"count": subcats_with_products, "total": total_subcats, "percent": round(subcats_with_products / total_subcats * 100, 1) if total_subcats else 0},
        },
        "sources": {
            "total": total_sources,
            "high": high_confidence,
            "medium": medium_confidence,
            "low": low_confidence,
        },
    }
