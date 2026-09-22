from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import date
from app.db import get_db
from app.models import PriceHistory, Sku
from app.schemas import SkuBase

router = APIRouter()


@router.get("/sku/{sku_id}")
def get_sku_price_history(sku_id: int, db: Session = Depends(get_db)):
    prices = db.query(PriceHistory).filter(
        PriceHistory.sku_id == sku_id
    ).order_by(desc(PriceHistory.recorded_date)).all()

    sku = db.query(Sku).filter(Sku.id == sku_id).first()

    return {
        "sku_id": sku_id,
        "current_mrp": float(sku.mrp) if sku and sku.mrp else None,
        "current_price": float(sku.selling_price) if sku and sku.selling_price else None,
        "history": [
            {
                "id": p.id,
                "mrp": float(p.mrp) if p.mrp else None,
                "selling_price": float(p.selling_price) if p.selling_price else None,
                "discount_percent": float(p.discount_percent) if p.discount_percent else None,
                "recorded_date": p.recorded_date.isoformat() if p.recorded_date else None,
                "source_url": p.source_url,
            }
            for p in prices
        ],
        "count": len(prices),
    }


@router.post("/sku/{sku_id}")
def record_price(sku_id: int, data: dict, db: Session = Depends(get_db)):
    sku = db.query(Sku).filter(Sku.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    record = PriceHistory(
        sku_id=sku_id,
        mrp=data.get("mrp", sku.mrp),
        selling_price=data.get("selling_price", sku.selling_price),
        discount_percent=data.get("discount_percent"),
        source_url=data.get("source_url"),
        recorded_date=date.today(),
    )
    db.add(record)
    db.commit()
    return {"status": "recorded", "id": record.id}


@router.get("/company/{company_id}")
def get_company_price_trends(company_id: int, db: Session = Depends(get_db)):
    from app.models import Brand, Product
    brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == company_id).all()]
    product_ids = [p.id for p in db.query(Product).filter(Product.brand_id.in_(brand_ids)).all()]
    sku_ids = [s.id for s in db.query(Sku).filter(Sku.product_id.in_(product_ids)).all()]

    prices = db.query(PriceHistory).filter(
        PriceHistory.sku_id.in_(sku_ids)
    ).order_by(desc(PriceHistory.recorded_date)).limit(100).all()

    return {
        "company_id": company_id,
        "total_price_records": len(prices),
        "skus_with_history": len(set(p.sku_id for p in prices)),
        "history": [
            {
                "sku_id": p.sku_id,
                "mrp": float(p.mrp) if p.mrp else None,
                "selling_price": float(p.selling_price) if p.selling_price else None,
                "recorded_date": p.recorded_date.isoformat() if p.recorded_date else None,
            }
            for p in prices
        ],
    }
