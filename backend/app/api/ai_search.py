import re
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import Optional
from app.db import get_db
from app.models import (
    Company, Brand, Product, Sku, Retailer, Category, Subcategory,
    OwnershipType, Region, CompanyRegion, SkuRetailer
)

router = APIRouter()


def extract_filters(query: str) -> dict:
    """Extract structured filters from natural language query."""
    q = query.lower().strip()
    filters = {}

    # Company types
    if "cooperative" in q or "co-op" in q:
        filters["ownership_type"] = "cooperative"
    elif "listed" in q or "public" in q:
        filters["ownership_type"] = "listed"
    elif "unlisted" in q or "private" in q:
        filters["ownership_type"] = "unlisted"
    elif "global" in q or "mnc" in q or "multinational" in q:
        filters["ownership_type"] = "global"

    # Regions
    region_map = {
        "north": ["north india", "north", "delhi", "punjab", "haryana", "up", "uttar pradesh", "rajasthan"],
        "west": ["west india", "west", "maharashtra", "gujarat", "mp", "madhya pradesh", "goa"],
        "south": ["south india", "south", "karnataka", "tamil nadu", "andhra", "telangana", "kerala"],
        "east": ["east india", "east", "west bengal", "bihar", "odisha"],
    }
    for region, keywords in region_map.items():
        for kw in keywords:
            if kw in q:
                filters["region"] = region
                break

    # Categories
    category_keywords = {
        "milk": ["milk"],
        "paneer": ["paneer", "cottage cheese"],
        "cheese": ["cheese"],
        "ghee": ["ghee", "clarified butter"],
        "curd": ["curd", "dahi", "yogurt"],
        "butter": ["butter"],
        "ice cream": ["ice cream", "icecream", "frozen"],
    }
    for cat, keywords in category_keywords.items():
        for kw in keywords:
            if kw in q:
                filters["category"] = cat
                break

    # Channel
    if "quick commerce" in q or "blinkit" in q or "zepto" in q or "instamart" in q:
        filters["channel"] = "quick_commerce"
    elif "ecommerce" in q or "e-commerce" in q or "online" in q or "amazon" in q or "flipkart" in q:
        filters["channel"] = "ecommerce"
    elif "modern trade" in q or "supermarket" in q or "dmart" in q or "reliance" in q:
        filters["channel"] = "modern_trade"
    elif "general trade" in q or "kirana" in q or "local" in q:
        filters["channel"] = "general_trade"

    # Specific company name (quoted or after "of")
    quoted = re.findall(r'"([^"]+)"', query)
    if quoted:
        filters["company_name"] = quoted[0]
    else:
        of_match = re.search(r'(?:of|for|about)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:in|selling|with|at|from)|\?|$)', query)
        if of_match:
            filters["company_name"] = of_match.group(1).strip()

    return filters


@router.post("")
def ai_search(data: dict, db: Session = Depends(get_db)):
    query = data.get("query", "")
    filters = extract_filters(query)

    results = {}
    summary_parts = []

    # Search companies
    company_q = db.query(Company).options(
        joinedload(Company.ownership_type),
        joinedload(Company.headquarters_region),
    )
    if "ownership_type" in filters:
        ot = db.query(OwnershipType).filter(OwnershipType.name == filters["ownership_type"]).first()
        if ot:
            company_q = company_q.filter(Company.ownership_type_id == ot.id)
    if "company_name" in filters:
        company_q = company_q.filter(Company.name.ilike(f"%{filters['company_name']}%"))
    if "region" in filters:
        region_names = {
            "north": ["Delhi NCR", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan"],
            "west": ["Maharashtra", "Gujarat", "Madhya Pradesh", "Goa"],
            "south": ["Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Kerala"],
            "east": ["West Bengal", "Bihar", "Odisha"],
        }
        region_ids = []
        for rn in region_names.get(filters["region"], []):
            reg = db.query(Region).filter(Region.name == rn).first()
            if reg:
                region_ids.append(reg.id)
        if region_ids:
            cr_subq = db.query(CompanyRegion.company_id).filter(CompanyRegion.region_id.in_(region_ids)).subquery()
            company_q = company_q.filter(Company.id.in_(cr_subq))

    companies = company_q.limit(20).all()
    results["companies"] = [
        {
            "id": c.id,
            "name": c.name,
            "ownership_type": c.ownership_type.name if c.ownership_type else None,
            "headquarters_region": c.headquarters_region.name if c.headquarters_region else None,
            "is_listed": c.is_listed,
            "is_global": c.is_global,
        }
        for c in companies
    ]
    if companies:
        summary_parts.append(f"Found {len(companies)} companies")

    # Search SKUs
    if "category" in filters or "channel" in filters:
        sku_q = db.query(Sku).options(
            joinedload(Sku.product).joinedload(Product.brand).joinedload(Brand.company),
            joinedload(Sku.product).joinedload(Product.subcategory).joinedload(Subcategory.category),
        )

        if "category" in filters:
            cat = db.query(Category).filter(Category.name.ilike(f"%{filters['category']}%")).first()
            if cat:
                subcat_ids = [s.id for s in db.query(Subcategory).filter(Subcategory.category_id == cat.id).all()]
                product_ids = [p.id for p in db.query(Product).filter(Product.subcategory_id.in_(subcat_ids)).all()]
                sku_q = sku_q.filter(Sku.product_id.in_(product_ids))

        if "channel" in filters:
            channel_sku_ids = [sr.sku_id for sr in db.query(SkuRetailer).filter(SkuRetailer.channel == filters["channel"]).all()]
            sku_q = sku_q.filter(Sku.id.in_(channel_sku_ids))

        if "region" in filters:
            region_names = {
                "north": ["Delhi NCR", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan"],
                "west": ["Maharashtra", "Gujarat", "Madhya Pradesh", "Goa"],
                "south": ["Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Kerala"],
                "east": ["West Bengal", "Bihar", "Odisha"],
            }
            region_ids = []
            for rn in region_names.get(filters["region"], []):
                reg = db.query(Region).filter(Region.name == rn).first()
                if reg:
                    region_ids.append(reg.id)
            if region_ids:
                region_sku_ids = [sr.sku_id for sr in db.query(SkuRetailer).filter(SkuRetailer.region_id.in_(region_ids)).all()]
                sku_q = sku_q.filter(Sku.id.in_(region_sku_ids))

        skus = sku_q.limit(30).all()
        results["skus"] = [
            {
                "id": s.id,
                "company": s.product.brand.company.name if s.product and s.product.brand and s.product.brand.company else "Unknown",
                "brand": s.product.brand.name if s.product and s.product.brand else "Unknown",
                "product": s.product.name if s.product else "Unknown",
                "category": s.product.subcategory.category.name if s.product and s.product.subcategory and s.product.subcategory.category else "Unknown",
                "subcategory": s.product.subcategory.name if s.product and s.product.subcategory else "Unknown",
                "variant": s.variant,
                "pack_size": float(s.pack_size) if s.pack_size else None,
                "unit": s.unit,
                "mrp": float(s.mrp) if s.mrp else None,
                "selling_price": float(s.selling_price) if s.selling_price else None,
            }
            for s in skus
        ]
        if skus:
            summary_parts.append(f"Found {len(skus)} SKUs")

    # Search retailers
    retailer_q = db.query(Retailer)
    if "channel" in filters:
        retailer_q = retailer_q.filter(Retailer.type == filters["channel"])
    retailers = retailer_q.limit(10).all()
    results["retailers"] = [
        {"id": r.id, "name": r.name, "type": r.type}
        for r in retailers
    ]
    if retailers:
        summary_parts.append(f"Found {len(retailers)} retailers")

    summary = ". ".join(summary_parts) if summary_parts else "No matching results found."

    return {
        "query": query,
        "filters": filters,
        "summary": summary,
        "results": results,
    }
