from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, Date, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class OwnershipType(Base):
    __tablename__ = "ownership_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    companies = relationship("Company", back_populates="ownership_type")


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    level = Column(String(20), nullable=False)  # region, state, city
    parent_id = Column(Integer, ForeignKey("regions.id"))

    parent = relationship("Region", remote_side=[id])
    company_regions = relationship("CompanyRegion", back_populates="region")
    sku_retailers = relationship("SkuRetailer", back_populates="region")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    ownership_type_id = Column(Integer, ForeignKey("ownership_types.id"))
    parent_company = Column(String(200))
    website = Column(String(500))
    headquarters_region_id = Column(Integer, ForeignKey("regions.id"))
    origin_region_id = Column(Integer, ForeignKey("regions.id"))
    is_listed = Column(Boolean, default=False)
    is_global = Column(Boolean, default=False)
    description = Column(Text)
    source_url = Column(String(500))
    source_date = Column(Date)
    confidence = Column(String(20), default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ownership_type = relationship("OwnershipType", back_populates="companies")
    headquarters_region = relationship("Region", foreign_keys=[headquarters_region_id])
    origin_region = relationship("Region", foreign_keys=[origin_region_id])
    brands = relationship("Brand", back_populates="company")
    company_regions = relationship("CompanyRegion", back_populates="company")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False)
    description = Column(Text)
    source_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("company_id", "name"),)

    company = relationship("Company", back_populates="brands")
    products = relationship("Product", back_populates="brand")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)

    subcategories = relationship("Subcategory", back_populates="category")


class Subcategory(Base):
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)

    __table_args__ = (UniqueConstraint("category_id", "name"),)

    category = relationship("Category", back_populates="subcategories")
    products = relationship("Product", back_populates="subcategory")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=False)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False)
    description = Column(Text)
    source_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("brand_id", "subcategory_id", "name"),)

    brand = relationship("Brand", back_populates="products")
    subcategory = relationship("Subcategory", back_populates="products")
    skus = relationship("Sku", back_populates="product")


class Sku(Base):
    __tablename__ = "skus"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant = Column(String(100))
    pack_size = Column(Numeric(10, 2))
    unit = Column(String(20))
    packaging_type = Column(String(50))
    mrp = Column(Numeric(10, 2))
    selling_price = Column(Numeric(10, 2))
    fat_percent = Column(Numeric(5, 2))
    protein_percent = Column(Numeric(5, 2))
    shelf_life_days = Column(Integer)
    storage_requirement = Column(String(50))
    flavour = Column(String(100))
    target_segment = Column(String(100))
    status = Column(String(20), default="active")
    source_url = Column(String(500))
    source_date = Column(Date)
    last_verified = Column(Date)
    confidence = Column(String(20), default="medium")
    canonical_sku_id = Column(Integer, ForeignKey("skus.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="skus")
    canonical = relationship("Sku", remote_side=[id])
    sku_retailers = relationship("SkuRetailer", back_populates="sku")


class Retailer(Base):
    __tablename__ = "retailers"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50))
    parent_company = Column(String(200))
    website = Column(String(500))
    source_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sku_retailers = relationship("SkuRetailer", back_populates="retailer")


class SkuRetailer(Base):
    __tablename__ = "sku_retailers"

    id = Column(Integer, primary_key=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"))
    channel = Column(String(50))
    available = Column(Boolean, default=True)
    source_url = Column(String(500))
    source_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("sku_id", "retailer_id", "region_id"),)

    sku = relationship("Sku", back_populates="sku_retailers")
    retailer = relationship("Retailer", back_populates="sku_retailers")
    region = relationship("Region", back_populates="sku_retailers")


class Distributor(Base):
    __tablename__ = "distributors"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50))  # national, regional, local
    territory = Column(String(200))
    state = Column(String(100))
    city = Column(String(100))
    district = Column(String(100))
    retailer_count = Column(Integer)
    product_categories = Column(Text)  # JSON array
    channel = Column(String(50))
    is_active = Column(Boolean, default=True)
    website = Column(String(500))
    source_url = Column(String(500))
    confidence = Column(String(20), default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company_distributors = relationship("CompanyDistributor", back_populates="distributor")


class CompanyDistributor(Base):
    __tablename__ = "company_distributors"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    distributor_id = Column(Integer, ForeignKey("distributors.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"))
    is_primary = Column(Boolean, default=False)
    source_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("company_id", "distributor_id"),)

    company = relationship("Company")
    distributor = relationship("Distributor", back_populates="company_distributors")
    brand = relationship("Brand")


class CompanyRegion(Base):
    __tablename__ = "company_regions"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    is_primary = Column(Boolean, default=False)
    source_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("company_id", "region_id"),)

    company = relationship("Company", back_populates="company_regions")
    region = relationship("Region", back_populates="company_regions")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    source_type = Column(String(50))
    source_url = Column(String(500))
    extracted_fact = Column(Text)
    extraction_date = Column(Date)
    last_verified = Column(Date)
    confidence = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    mrp = Column(Numeric(10, 2))
    selling_price = Column(Numeric(10, 2))
    discount_percent = Column(Numeric(5, 2))
    source_url = Column(String(500))
    recorded_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sku = relationship("Sku")


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    description = Column(Text)
    source_url = Column(String(500))
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SavedAnalysis(Base):
    __tablename__ = "saved_analyses"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    filters = Column(Text)  # JSON
    results = Column(Text)  # JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    region_id = Column(Integer, ForeignKey("regions.id"))
    event_types = Column(Text)  # JSON array of event types to watch
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company")
    category = relationship("Category")
    region = relationship("Region")
    notifications = relationship("AlertNotification", back_populates="alert")


class AlertNotification(Base):
    __tablename__ = "alert_notifications"

    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    change_event_id = Column(Integer, ForeignKey("change_events.id"))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    alert = relationship("Alert", back_populates="notifications")
    change_event = relationship("ChangeEvent")


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer)
    action = Column(String(50), nullable=False)  # new, update, merge, ambiguous
    status = Column(String(20), default="pending")  # pending, approved, rejected, merged
    data = Column(Text)  # JSON - the proposed data
    notes = Column(Text)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
