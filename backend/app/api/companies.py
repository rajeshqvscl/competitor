from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional, List
from app.db import get_db
from app.models import Company, Brand, Sku, CompanyRegion, OwnershipType, Region
from app.schemas import Company as CompanySchema, CompanyListItem, Brand as BrandSchema, Sku as SkuSchema, CompanyCreate

router = APIRouter()


@router.get("", response_model=List[CompanyListItem])
def list_companies(
    ownership_type: Optional[str] = None,
    region_id: Optional[int] = None,
    is_listed: Optional[bool] = None,
    is_global: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Company).options(
        joinedload(Company.ownership_type),
        joinedload(Company.headquarters_region),
    )
    if ownership_type:
        q = q.join(OwnershipType).filter(OwnershipType.name == ownership_type)
    if region_id:
        q = q.join(CompanyRegion).filter(CompanyRegion.region_id == region_id)
    if is_listed is not None:
        q = q.filter(Company.is_listed == is_listed)
    if is_global is not None:
        q = q.filter(Company.is_global == is_global)
    if search:
        q = q.filter(Company.name.ilike(f"%{search}%"))
    return q.offset(skip).limit(limit).all()


@router.get("/{company_id}", response_model=CompanySchema)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).options(
        joinedload(Company.ownership_type),
        joinedload(Company.headquarters_region),
        joinedload(Company.origin_region),
    ).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("", response_model=CompanySchema)
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}/brands", response_model=List[BrandSchema])
def get_company_brands(company_id: int, db: Session = Depends(get_db)):
    return db.query(Brand).filter(Brand.company_id == company_id).all()


@router.get("/{company_id}/skus", response_model=List[SkuSchema])
def get_company_skus(
    company_id: int,
    category_id: Optional[int] = None,
    subcategory_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Sku).join(Sku.product).join(Sku.product).filter(
        Sku.product.has(brand_id=Brand.id),
        Brand.company_id == company_id,
    )
    if subcategory_id:
        q = q.filter(Sku.product.has(subcategory_id=subcategory_id))
    if category_id:
        from app.models import Subcategory
        q = q.join(Subcategory, Sku.product.has(subcategory_id=Subcategory.id)).filter(
            Subcategory.category_id == category_id
        )
    return q.all()


@router.get("/{company_id}/competitors")
def get_company_competitors(
    company_id: int,
    region_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    target = db.query(Company).filter(Company.id == company_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Company not found")

    target_brand_ids = [b.id for b in db.query(Brand).filter(Brand.company_id == company_id).all()]
    if not target_brand_ids:
        return []

    target_subcats = set()
    from app.models import Product
    products = db.query(Product).filter(Product.brand_id.in_(target_brand_ids)).all()
    for p in products:
        target_subcats.add(p.subcategory_id)

    target_regions = set()
    company_regions = db.query(CompanyRegion).filter(CompanyRegion.company_id == company_id).all()
    for cr in company_regions:
        target_regions.add(cr.region_id)

    competitor_ids = set()
    for subcat_id in target_subcats:
        product_brand_ids = [p.brand_id for p in db.query(Product).filter(Product.subcategory_id == subcat_id).all()]
        for bid in product_brand_ids:
            if bid not in target_brand_ids:
                brand = db.query(Brand).filter(Brand.id == bid).first()
                if brand:
                    competitor_ids.add(brand.company_id)

    competitors = db.query(Company).options(
        joinedload(Company.ownership_type),
        joinedload(Company.headquarters_region),
    ).filter(Company.id.in_(competitor_ids)).all()

    result = []
    for comp in competitors:
        comp_regions = set()
        for cr in db.query(CompanyRegion).filter(CompanyRegion.company_id == comp.id).all():
            comp_regions.add(cr.region_id)
        shared_regions = target_regions & comp_regions
        comp_subcats = set()
        comp_products = db.query(Product).join(Brand).filter(Brand.company_id == comp.id).all()
        for p in comp_products:
            comp_subcats.add(p.subcategory_id)
        shared_subcats = target_subcats & comp_subcats

        result.append({
            "company": comp,
            "shared_categories": len(shared_subcats),
            "total_target_categories": len(target_subcats),
            "shared_regions": len(shared_regions),
            "total_target_regions": len(target_regions),
            "category_overlap": round(len(shared_subcats) / len(target_subcats), 2) if target_subcats else 0,
            "region_overlap": round(len(shared_regions) / len(target_regions), 2) if target_regions else 0,
        })

    result.sort(key=lambda x: x["category_overlap"], reverse=True)
    return result
