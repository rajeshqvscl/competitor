from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.models import Retailer, SkuRetailer, Sku
from app.schemas import Retailer as RetailerSchema, SkuRetailer as SkuRetailerSchema

router = APIRouter()


@router.get("", response_model=List[RetailerSchema])
def list_retailers(db: Session = Depends(get_db)):
    return db.query(Retailer).all()


@router.get("/{retailer_id}", response_model=RetailerSchema)
def get_retailer(retailer_id: int, db: Session = Depends(get_db)):
    retailer = db.query(Retailer).filter(Retailer.id == retailer_id).first()
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")
    return retailer


@router.get("/{retailer_id}/products")
def get_retailer_products(retailer_id: int, db: Session = Depends(get_db)):
    skus = db.query(Sku).join(SkuRetailer).filter(SkuRetailer.retailer_id == retailer_id).all()
    return skus
