from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class OwnershipTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class OwnershipType(OwnershipTypeBase):
    id: int
    model_config = {"from_attributes": True}


class RegionBase(BaseModel):
    name: str
    level: str
    parent_id: Optional[int] = None

class Region(RegionBase):
    id: int
    model_config = {"from_attributes": True}


class CompanyBase(BaseModel):
    name: str
    slug: str
    ownership_type_id: Optional[int] = None
    parent_company: Optional[str] = None
    website: Optional[str] = None
    headquarters_region_id: Optional[int] = None
    origin_region_id: Optional[int] = None
    is_listed: bool = False
    is_global: bool = False
    description: Optional[str] = None

class CompanyCreate(CompanyBase):
    source_url: Optional[str] = None
    confidence: str = "medium"

class Company(CompanyBase):
    id: int
    source_url: Optional[str] = None
    confidence: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ownership_type: Optional[OwnershipType] = None
    headquarters_region: Optional[Region] = None
    model_config = {"from_attributes": True}

class CompanyListItem(BaseModel):
    id: int
    name: str
    slug: str
    is_listed: bool
    is_global: bool
    ownership_type: Optional[OwnershipType] = None
    headquarters_region: Optional[Region] = None
    model_config = {"from_attributes": True}


class BrandBase(BaseModel):
    name: str
    slug: str
    company_id: int
    description: Optional[str] = None

class BrandCreate(BrandBase):
    source_url: Optional[str] = None

class Brand(BrandBase):
    id: int
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None

class Category(CategoryBase):
    id: int
    model_config = {"from_attributes": True}


class SubcategoryBase(BaseModel):
    name: str
    slug: str
    category_id: int
    description: Optional[str] = None

class Subcategory(SubcategoryBase):
    id: int
    model_config = {"from_attributes": True}


class ProductBase(BaseModel):
    name: str
    slug: str
    brand_id: int
    subcategory_id: int
    description: Optional[str] = None

class ProductCreate(ProductBase):
    source_url: Optional[str] = None

class Product(ProductBase):
    id: int
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SkuBase(BaseModel):
    product_id: int
    variant: Optional[str] = None
    pack_size: Optional[Decimal] = None
    unit: Optional[str] = None
    packaging_type: Optional[str] = None
    mrp: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    fat_percent: Optional[Decimal] = None
    protein_percent: Optional[Decimal] = None
    shelf_life_days: Optional[int] = None
    storage_requirement: Optional[str] = None
    flavour: Optional[str] = None
    target_segment: Optional[str] = None
    status: str = "active"

class SkuCreate(SkuBase):
    source_url: Optional[str] = None
    confidence: str = "medium"

class Sku(SkuBase):
    id: int
    source_url: Optional[str] = None
    source_date: Optional[date] = None
    last_verified: Optional[date] = None
    confidence: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SkuWithProduct(Sku):
    product_name: Optional[str] = None
    brand_name: Optional[str] = None
    company_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    category_name: Optional[str] = None


class RetailerBase(BaseModel):
    name: str
    type: Optional[str] = None
    parent_company: Optional[str] = None
    website: Optional[str] = None

class RetailerCreate(RetailerBase):
    source_url: Optional[str] = None

class Retailer(RetailerBase):
    id: int
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SkuRetailerBase(BaseModel):
    sku_id: int
    retailer_id: int
    region_id: Optional[int] = None
    channel: Optional[str] = None
    available: bool = True

class SkuRetailer(SkuRetailerBase):
    id: int
    source_url: Optional[str] = None
    source_date: Optional[date] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class CompanyRegionBase(BaseModel):
    company_id: int
    region_id: int
    is_primary: bool = False

class CompanyRegion(CompanyRegionBase):
    id: int
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SourceBase(BaseModel):
    entity_type: str
    entity_id: int
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    extracted_fact: Optional[str] = None
    confidence: Optional[str] = None

class Source(SourceBase):
    id: int
    extraction_date: Optional[date] = None
    last_verified: Optional[date] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class CompetitorAnalysisRequest(BaseModel):
    company_id: int
    region_id: Optional[int] = None
    category_id: Optional[int] = None
    channel: Optional[str] = None


class PortfolioComparisonRequest(BaseModel):
    company_ids: List[int]
    category_id: Optional[int] = None
    region_id: Optional[int] = None


class SkuComparisonRequest(BaseModel):
    company_ids: List[int]
    subcategory_id: int
    region_id: Optional[int] = None
    pack_size: Optional[Decimal] = None


class DashboardStats(BaseModel):
    total_companies: int
    total_brands: int
    total_products: int
    total_skus: int
    total_retailers: int
    total_regions: int
    companies_by_ownership: dict
    companies_by_region: dict
    skus_by_category: dict
