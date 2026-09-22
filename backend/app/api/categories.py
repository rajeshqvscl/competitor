from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.models import Category, Subcategory, Product, Brand
from app.schemas import Category as CategorySchema, Subcategory as SubcategorySchema, Product as ProductSchema

router = APIRouter()


@router.get("", response_model=List[CategorySchema])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.get("/{category_id}/subcategories", response_model=List[SubcategorySchema])
def list_subcategories(category_id: int, db: Session = Depends(get_db)):
    return db.query(Subcategory).filter(Subcategory.category_id == category_id).all()


@router.get("/{category_id}/products", response_model=List[ProductSchema])
def list_category_products(category_id: int, db: Session = Depends(get_db)):
    return db.query(Product).join(Subcategory).filter(Subcategory.category_id == category_id).all()
