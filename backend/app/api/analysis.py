from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from app.db import get_db
from app.models import (
    Company, Brand, Product, Sku, Category, Subcategory,
    Retailer, SkuRetailer, CompanyRegion, Region
)
from app.schemas import (
    CompetitorAnalysisRequest, PortfolioComparisonRequest,
    SkuComparisonRequest, SkuWithProduct
)

router = APIRouter()


@router.post("/competitors")
def competitor_analysis(req: CompetitorAnalysisRequest, db: Session = Depends(get_db)):
    target = db.query(Company).options(
        joinedload(Company.ownership_type),
        joinedload(Company.headquarters_region),
    ).filter(Company.id == req.company_id).first()
    if not target:
        return {"error": "Company not found"}

    target_brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == req.company_id).all()]

    target_subcats = set()
    target_products = db.query(Product).filter(Product.brand_id.in_(target_brand_ids)).all()
    for p in target_products:
        target_subcats.add(p.subcategory_id)

    target_regions = set()
    for cr in db.query(CompanyRegion).filter(CompanyRegion.company_id == req.company_id).all():
        target_regions.add(cr.region_id)

    # Find companies sharing subcategories
    competitor_data = {}
    for subcat_id in target_subcats:
        product_brand_ids = [p.brand_id for p in db.query(Product).filter(Product.subcategory_id == subcat_id).all()]
        for bid in product_brand_ids:
            if bid not in target_brand_ids:
                brand = db.query(Brand).filter(Brand.id == bid).first()
                if brand and brand.company_id not in competitor_data:
                    competitor_data[brand.company_id] = {"shared_subcats": set(), "shared_regions": set()}
                if brand:
                    competitor_data[brand.company_id]["shared_subcats"].add(subcat_id)

    # Region overlap
    for comp_id in competitor_data:
        for cr in db.query(CompanyRegion).filter(CompanyRegion.company_id == comp_id).all():
            if cr.region_id in target_regions:
                competitor_data[comp_id]["shared_regions"].add(cr.region_id)

    # Filter by region if specified
    if req.region_id:
        competitor_data = {
            cid: data for cid, data in competitor_data.items()
            if req.region_id in data["shared_regions"]
        }

    # Build response
    competitors = []
    for comp_id, data in competitor_data.items():
        comp = db.query(Company).options(
            joinedload(Company.ownership_type),
            joinedload(Company.headquarters_region),
        ).filter(Company.id == comp_id).first()
        if not comp:
            continue

        cat_overlap = round(len(data["shared_subcats"]) / len(target_subcats), 2) if target_subcats else 0
        reg_overlap = round(len(data["shared_regions"]) / len(target_regions), 2) if target_regions else 0

        competitors.append({
            "company": {
                "id": comp.id,
                "name": comp.name,
                "slug": comp.slug,
                "is_listed": comp.is_listed,
                "is_global": comp.is_global,
                "ownership_type": comp.ownership_type.name if comp.ownership_type else None,
                "headquarters_region": comp.headquarters_region.name if comp.headquarters_region else None,
            },
            "shared_categories": len(data["shared_subcats"]),
            "total_target_categories": len(target_subcats),
            "shared_regions": len(data["shared_regions"]),
            "total_target_regions": len(target_regions),
            "category_overlap": cat_overlap,
            "region_overlap": reg_overlap,
        })

    competitors.sort(key=lambda x: x["category_overlap"], reverse=True)

    return {
        "target_company": {
            "id": target.id,
            "name": target.name,
            "ownership_type": target.ownership_type.name if target.ownership_type else None,
            "headquarters_region": target.headquarters_region.name if target.headquarters_region else None,
        },
        "filters": {
            "region_id": req.region_id,
            "category_id": req.category_id,
            "channel": req.channel,
        },
        "competitors": competitors,
        "summary": {
            "total_competitors": len(competitors),
            "target_categories": len(target_subcats),
            "target_regions": len(target_regions),
        }
    }


@router.post("/portfolio")
def portfolio_comparison(req: PortfolioComparisonRequest, db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    result = []

    for cat in categories:
        subcats = db.query(Subcategory).filter(Subcategory.category_id == cat.id).all()
        subcat_ids = [s.id for s in subcats]

        row = {"category": cat.name, "category_id": cat.id, "companies": {}}
        for cid in req.company_ids:
            brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == cid).all()]
            product_count = db.query(Product).filter(
                Product.brand_id.in_(brand_ids),
                Product.subcategory_id.in_(subcat_ids),
            ).count()
            row["companies"][cid] = product_count > 0
        result.append(row)

    return {"comparison": result, "company_ids": req.company_ids}


@router.post("/sku-comparison")
def sku_comparison(req: SkuComparisonRequest, db: Session = Depends(get_db)):
    results = []
    for cid in req.company_ids:
        brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == cid).all()]
        product_ids = [p.id for p in db.query(Product).filter(
            Product.brand_id.in_(brand_ids),
            Product.subcategory_id == req.subcategory_id,
        ).all()]

        skus = db.query(Sku).options(
            joinedload(Sku.product).joinedload(Product.brand),
            joinedload(Sku.product).joinedload(Product.subcategory),
        ).filter(Sku.product_id.in_(product_ids), Sku.status == "active").all()

        if req.pack_size:
            skus = [s for s in skus if s.pack_size == req.pack_size]

        company = db.query(Company).filter(Company.id == cid).first()
        for sku in skus:
            results.append({
                "company_name": company.name if company else "Unknown",
                "company_id": cid,
                "brand_name": sku.product.brand.name if sku.product and sku.product.brand else "Unknown",
                "product_name": sku.product.name if sku.product else "Unknown",
                "subcategory": sku.product.subcategory.name if sku.product and sku.product.subcategory else "Unknown",
                "variant": sku.variant,
                "pack_size": float(sku.pack_size) if sku.pack_size else None,
                "unit": sku.unit,
                "mrp": float(sku.mrp) if sku.mrp else None,
                "selling_price": float(sku.selling_price) if sku.selling_price else None,
                "fat_percent": float(sku.fat_percent) if sku.fat_percent else None,
                "status": sku.status,
                "id": sku.id,
            })

    results.sort(key=lambda x: (x["pack_size"] or 0, x["mrp"] or 0))
    return {"skus": results, "company_ids": req.company_ids, "subcategory_id": req.subcategory_id}


@router.post("/retailer-overlap")
def retailer_overlap(req: PortfolioComparisonRequest, db: Session = Depends(get_db)):
    retailers = db.query(Retailer).all()
    result = []

    for retailer in retailers:
        row = {"retailer": retailer.name, "retailer_id": retailer.id, "type": retailer.type, "companies": {}}
        for cid in req.company_ids:
            sku_ids = [s.id for s in db.query(Sku).join(Product).join(Brand).filter(Brand.company_id == cid).all()]
            count = db.query(SkuRetailer).filter(
                SkuRetailer.sku_id.in_(sku_ids),
                SkuRetailer.retailer_id == retailer.id,
            ).count()
            row["companies"][cid] = count > 0
        result.append(row)

    return {"overlap": result, "company_ids": req.company_ids}


@router.post("/white-space")
def white_space_analysis(req: PortfolioComparisonRequest, db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    gaps = []

    for cat in categories:
        subcats = db.query(Subcategory).filter(Subcategory.category_id == cat.id).all()
        for subcat in subcats:
            presence = {}
            for cid in req.company_ids:
                brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == cid).all()]
                count = db.query(Product).filter(
                    Product.brand_id.in_(brand_ids),
                    Product.subcategory_id == subcat.id,
                ).count()
                presence[cid] = count > 0

            present_count = sum(1 for v in presence.values() if v)
            if present_count < len(req.company_ids):
                company_names = {}
                for cid in req.company_ids:
                    co = db.query(Company).filter(Company.id == cid).first()
                    company_names[cid] = co.name if co else str(cid)

                gaps.append({
                    "category": cat.name,
                    "subcategory": subcat.name,
                    "present_companies": [company_names[cid] for cid, v in presence.items() if v],
                    "absent_companies": [company_names[cid] for cid, v in presence.items() if not v],
                    "gap_count": len(req.company_ids) - present_count,
                })

    gaps.sort(key=lambda x: x["gap_count"], reverse=True)
    return {"gaps": gaps, "company_ids": req.company_ids}
