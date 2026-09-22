import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Optional
from app.db import get_db
from app.models import Distributor, CompanyDistributor, Company

router = APIRouter()


@router.get("")
def list_distributors(
    state: Optional[str] = None,
    city: Optional[str] = None,
    distributor_type: Optional[str] = None,
    channel: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Distributor)
    if state:
        q = q.filter(Distributor.state.ilike(f"%{state}%"))
    if city:
        q = q.filter(Distributor.city.ilike(f"%{city}%"))
    if distributor_type:
        q = q.filter(Distributor.type == distributor_type)
    if channel:
        q = q.filter(Distributor.channel == channel)
    if is_active is not None:
        q = q.filter(Distributor.is_active == is_active)
    if search:
        q = q.filter(Distributor.name.ilike(f"%{search}%"))
    distributors = q.order_by(Distributor.name).offset(skip).limit(limit).all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "type": d.type,
            "territory": d.territory,
            "state": d.state,
            "city": d.city,
            "district": d.district,
            "retailer_count": d.retailer_count,
            "product_categories": json.loads(d.product_categories) if d.product_categories else [],
            "channel": d.channel,
            "is_active": d.is_active,
            "confidence": d.confidence,
        }
        for d in distributors
    ]


@router.get("/{distributor_id}")
def get_distributor(distributor_id: int, db: Session = Depends(get_db)):
    d = db.query(Distributor).filter(Distributor.id == distributor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Distributor not found")

    company_rels = db.query(CompanyDistributor).options(
        joinedload(CompanyDistributor.company),
        joinedload(CompanyDistributor.brand),
    ).filter(CompanyDistributor.distributor_id == distributor_id).all()

    return {
        "id": d.id,
        "name": d.name,
        "type": d.type,
        "territory": d.territory,
        "state": d.state,
        "city": d.city,
        "district": d.district,
        "retailer_count": d.retailer_count,
        "product_categories": json.loads(d.product_categories) if d.product_categories else [],
        "channel": d.channel,
        "is_active": d.is_active,
        "website": d.website,
        "source_url": d.source_url,
        "confidence": d.confidence,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "companies": [
            {
                "company_id": rel.company_id,
                "company_name": rel.company.name if rel.company else "Unknown",
                "brand_name": rel.brand.name if rel.brand else None,
                "is_primary": rel.is_primary,
            }
            for rel in company_rels
        ],
    }


@router.post("")
def create_distributor(data: dict, db: Session = Depends(get_db)):
    d = Distributor(
        name=data["name"],
        type=data.get("type"),
        territory=data.get("territory"),
        state=data.get("state"),
        city=data.get("city"),
        district=data.get("district"),
        retailer_count=data.get("retailer_count"),
        product_categories=json.dumps(data.get("product_categories", [])),
        channel=data.get("channel"),
        is_active=data.get("is_active", True),
        website=data.get("website"),
        source_url=data.get("source_url"),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"status": "created", "id": d.id}


@router.put("/{distributor_id}")
def update_distributor(distributor_id: int, data: dict, db: Session = Depends(get_db)):
    d = db.query(Distributor).filter(Distributor.id == distributor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Distributor not found")
    for field in ["name", "type", "territory", "state", "city", "district",
                   "retailer_count", "channel", "is_active", "website", "source_url"]:
        if field in data:
            setattr(d, field, data[field])
    if "product_categories" in data:
        d.product_categories = json.dumps(data["product_categories"])
    db.commit()
    return {"status": "updated"}


@router.delete("/{distributor_id}")
def delete_distributor(distributor_id: int, db: Session = Depends(get_db)):
    d = db.query(Distributor).filter(Distributor.id == distributor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Distributor not found")
    db.delete(d)
    db.commit()
    return {"status": "deleted"}


@router.get("/company/{company_id}")
def get_company_distributors(company_id: int, db: Session = Depends(get_db)):
    rels = db.query(CompanyDistributor).options(
        joinedload(CompanyDistributor.distributor),
        joinedload(CompanyDistributor.brand),
    ).filter(CompanyDistributor.company_id == company_id).all()

    return [
        {
            "distributor_id": rel.distributor_id,
            "distributor_name": rel.distributor.name if rel.distributor else "Unknown",
            "distributor_type": rel.distributor.type if rel.distributor else None,
            "state": rel.distributor.state if rel.distributor else None,
            "city": rel.distributor.city if rel.distributor else None,
            "territory": rel.distributor.territory if rel.distributor else None,
            "brand_name": rel.brand.name if rel.brand else None,
            "is_primary": rel.is_primary,
        }
        for rel in rels
    ]
