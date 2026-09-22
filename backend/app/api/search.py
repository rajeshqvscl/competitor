from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.db import get_db
from app.models import Company, Brand, Product, Sku, Retailer, Subcategory, Category

router = APIRouter()


@router.get("")
def search(
    q: str = "",
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not q:
        return {"results": []}

    pattern = f"%{q}%"
    results = []

    if not entity_type or entity_type == "company":
        companies = db.query(Company).filter(Company.name.ilike(pattern)).limit(10).all()
        for c in companies:
            results.append({"type": "company", "id": c.id, "name": c.name, "slug": c.slug})

    if not entity_type or entity_type == "brand":
        brands = db.query(Brand).filter(Brand.name.ilike(pattern)).limit(10).all()
        for b in brands:
            results.append({"type": "brand", "id": b.id, "name": b.name, "company_id": b.company_id})

    if not entity_type or entity_type == "product":
        products = db.query(Product).filter(Product.name.ilike(pattern)).limit(10).all()
        for p in products:
            results.append({"type": "product", "id": p.id, "name": p.name})

    if not entity_type or entity_type == "sku":
        skus = db.query(Sku).filter(
            or_(Sku.variant.ilike(pattern), Sku.flavour.ilike(pattern))
        ).limit(10).all()
        for s in skus:
            results.append({"type": "sku", "id": s.id, "variant": s.variant, "pack_size": float(s.pack_size) if s.pack_size else None})

    if not entity_type or entity_type == "retailer":
        retailers = db.query(Retailer).filter(Retailer.name.ilike(pattern)).limit(10).all()
        for r in retailers:
            results.append({"type": "retailer", "id": r.id, "name": r.name})

    return {"results": results, "query": q}
