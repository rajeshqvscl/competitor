import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.models import (
    Company, Brand, Product, Sku, Category, Subcategory,
    Retailer, SkuRetailer, CompanyRegion, Region
)

router = APIRouter()


@router.post("/sku-comparison")
def export_sku_comparison(data: dict, db: Session = Depends(get_db)):
    company_ids = data.get("company_ids", [])
    subcategory_id = data.get("subcategory_id")

    if not company_ids or not subcategory_id:
        return {"error": "company_ids and subcategory_id required"}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Company", "Brand", "Product", "Variant", "Pack Size", "Unit",
        "Packaging", "MRP", "Selling Price", "Fat %", "Protein %",
        "Shelf Life (days)", "Status", "Source URL", "Confidence"
    ])

    for cid in company_ids:
        brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == cid).all()]
        product_ids = [p.id for p in db.query(Product).filter(
            Product.brand_id.in_(brand_ids),
            Product.subcategory_id == subcategory_id,
        ).all()]

        company = db.query(Company).filter(Company.id == cid).first()
        skus = db.query(Sku).options(
            joinedload(Sku.product).joinedload(Product.brand),
        ).filter(Sku.product_id.in_(product_ids)).all()

        for sku in skus:
            writer.writerow([
                company.name if company else "",
                sku.product.brand.name if sku.product and sku.product.brand else "",
                sku.product.name if sku.product else "",
                sku.variant or "",
                sku.pack_size or "",
                sku.unit or "",
                sku.packaging_type or "",
                sku.mrp or "",
                sku.selling_price or "",
                sku.fat_percent or "",
                sku.protein_percent or "",
                sku.shelf_life_days or "",
                sku.status or "",
                sku.source_url or "",
                sku.confidence or "",
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sku_comparison.csv"},
    )


@router.post("/portfolio")
def export_portfolio(data: dict, db: Session = Depends(get_db)):
    company_ids = data.get("company_ids", [])
    if not company_ids:
        return {"error": "company_ids required"}

    categories = db.query(Category).all()
    output = io.StringIO()
    writer = csv.writer(output)

    company_names = []
    for cid in company_ids:
        co = db.query(Company).filter(Company.id == cid).first()
        company_names.append(co.name if co else str(cid))

    writer.writerow(["Category"] + company_names)

    for cat in categories:
        subcats = db.query(Subcategory).filter(Subcategory.category_id == cat.id).all()
        subcat_ids = [s.id for s in subcats]
        row = [cat.name]
        for cid in company_ids:
            brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == cid).all()]
            count = db.query(Product).filter(
                Product.brand_id.in_(brand_ids),
                Product.subcategory_id.in_(subcat_ids),
            ).count()
            row.append("Yes" if count > 0 else "No")
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio_comparison.csv"},
    )


@router.post("/retailer-overlap")
def export_retailer_overlap(data: dict, db: Session = Depends(get_db)):
    company_ids = data.get("company_ids", [])
    if not company_ids:
        return {"error": "company_ids required"}

    retailers = db.query(Retailer).all()
    output = io.StringIO()
    writer = csv.writer(output)

    company_names = []
    for cid in company_ids:
        co = db.query(Company).filter(Company.id == cid).first()
        company_names.append(co.name if co else str(cid))

    writer.writerow(["Retailer", "Type"] + company_names)

    for retailer in retailers:
        row = [retailer.name, retailer.type or ""]
        for cid in company_ids:
            sku_ids = [s.id for s in db.query(Sku).join(Product).join(Brand).filter(Brand.company_id == cid).all()]
            count = db.query(SkuRetailer).filter(
                SkuRetailer.sku_id.in_(sku_ids),
                SkuRetailer.retailer_id == retailer.id,
            ).count()
            row.append("Yes" if count > 0 else "No")
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=retailer_overlap.csv"},
    )
