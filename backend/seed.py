"""Seed database from CSV files."""
import csv
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal, engine, Base
from app.models import (
    OwnershipType, Region, Company, Brand, Category, Subcategory,
    Product, Sku, Retailer, SkuRetailer, CompanyRegion, Distributor,
    CompanyDistributor, PriceHistory, Source
)

# Base source attributed to seed-loaded data (company website is the source of record)
SEED_CONFIDENCE = "medium"


def company_url(company_name: str, company_map: dict, companies_rows: list[dict]) -> str | None:
    """Return the seed company's website URL (used as source_url for its data)."""
    row = next((r for r in companies_rows if r["name"] == company_name), None)
    return (row.get("website") or None) if row else None

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Required columns per CSV file
REQUIRED_COLUMNS = {
    "ownership_types.csv": ["name", "description"],
    "regions.csv": ["name", "level"],  # 'parent' is optional (empty for top-level regions)
    "companies.csv": ["name", "slug", "ownership_type", "headquarters_region", "is_listed", "is_global"],
    "brands.csv": ["company", "brand_name", "brand_slug"],
    "categories.csv": ["name", "slug", "description"],
    "subcategories.csv": ["category", "name", "slug"],
    "products.csv": ["name", "slug", "brand", "subcategory"],
    "skus.csv": ["product", "variant", "pack_size", "unit", "packaging_type", "mrp", "selling_price", "status"],
    "retailers.csv": ["name", "type"],
    "company_regions.csv": ["company", "region", "is_primary"],
    "distributors.csv": ["name", "type", "territory", "city", "state", "district", "channel"],
    "company_distributors.csv": ["company", "distributor"],
    "sku_retailers.csv": ["sku_product", "sku_variant", "retailer", "region", "channel", "available"],
    "price_history.csv": ["sku_product", "sku_variant", "mrp", "selling_price", "recorded_date"],
}


def slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "").replace("&", "and")


def validate_csv(filename: str, rows: list[dict]) -> list[str]:
    errors = []
    required = REQUIRED_COLUMNS.get(filename, [])
    if not rows:
        errors.append(f"{filename}: empty file")
        return errors
    actual_cols = set(rows[0].keys())
    missing = [c for c in required if c not in actual_cols]
    if missing:
        errors.append(f"{filename}: missing columns: {missing}")
    for i, row in enumerate(rows, 1):
        for col in required:
            val = row.get(col, "").strip()
            if not val:
                errors.append(f"{filename} row {i}: '{col}' is empty")
    return errors


def read_csv(filename: str) -> list[dict]:
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    errors = validate_csv(filename, rows)
    if errors:
        print(f"Validation errors in {filename}:")
        for e in errors:
            print(f"  - {e}")
        raise ValueError(f"CSV validation failed for {filename}")
    return rows


def table_empty(db, model):
    return db.query(model).count() == 0


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Ownership Types
        if table_empty(db, OwnershipType):
            print("Seeding ownership_types...")
            ownership_map = {}
            for row in read_csv("ownership_types.csv"):
                ot = OwnershipType(name=row["name"], description=row["description"])
                db.add(ot)
                db.flush()
                ownership_map[row["name"]] = ot.id
        else:
            print("ownership_types already exists, skipping...")
            ownership_map = {r.name: r.id for r in db.query(OwnershipType).all()}

        # 2. Regions
        if table_empty(db, Region):
            print("Seeding regions...")
            region_map = {}
            for row in read_csv("regions.csv"):
                parent_id = region_map.get(row["parent"]) if row["parent"] else None
                r = Region(name=row["name"], level=row["level"], parent_id=parent_id)
                db.add(r)
                db.flush()
                region_map[row["name"]] = r.id
        else:
            print("regions already exists, skipping...")
            region_map = {r.name: r.id for r in db.query(Region).all()}

        # 3. Companies
        if table_empty(db, Company):
            print("Seeding companies...")
            company_map = {}
            companies_rows = read_csv("companies.csv")
            for row in companies_rows:
                c = Company(
                    name=row["name"],
                    slug=row["slug"],
                    ownership_type_id=ownership_map.get(row["ownership_type"]),
                    parent_company=row["parent_company"] or None,
                    website=row["website"] or None,
                    headquarters_region_id=region_map.get(row["headquarters_region"]),
                    is_listed=row["is_listed"].lower() == "true",
                    is_global=row["is_global"].lower() == "true",
                    description=row.get("description") or None,
                    source_url=row["website"] or None,
                    source_date=date.today(),
                    confidence=SEED_CONFIDENCE,
                )
                db.add(c)
                db.flush()
                company_map[row["name"]] = c.id
        else:
            print("companies already exists, skipping...")
            company_map = {c.name: c.id for c in db.query(Company).all()}

        # 4. Brands
        if table_empty(db, Brand):
            print("Seeding brands...")
            brand_map = {}
            brands_rows = read_csv("brands.csv")
            for row in brands_rows:
                b = Brand(
                    company_id=company_map[row["company"]],
                    name=row["brand_name"],
                    slug=row["brand_slug"],
                    source_url=company_url(row["company"], company_map, companies_rows),
                )
                db.add(b)
                db.flush()
                brand_map[row["brand_name"]] = b.id
        else:
            print("brands already exists, skipping...")
            brand_map = {b.name: b.id for b in db.query(Brand).all()}
        company_name_by_brand = {}
        for row in read_csv("brands.csv"):
            if row["brand_name"] in brand_map:
                company_name_by_brand[row["brand_name"]] = row["company"]
        # product name -> company (via product -> brand -> company)
        product_company = {}
        for row in read_csv("products.csv"):
            comp = company_name_by_brand.get(row["brand"])
            if comp:
                product_company[row["name"]] = comp

        # 5. Categories
        if table_empty(db, Category):
            print("Seeding categories...")
            category_map = {}
            for row in read_csv("categories.csv"):
                cat = Category(name=row["name"], slug=row["slug"], description=row["description"])
                db.add(cat)
                db.flush()
                category_map[row["name"]] = cat.id
        else:
            print("categories already exists, skipping...")
            category_map = {c.name: c.id for c in db.query(Category).all()}

        # 6. Subcategories
        if table_empty(db, Subcategory):
            print("Seeding subcategories...")
            subcategory_map = {}
            for row in read_csv("subcategories.csv"):
                sc = Subcategory(
                    category_id=category_map[row["category"]],
                    name=row["name"],
                    slug=row["slug"],
                )
                db.add(sc)
                db.flush()
                subcategory_map[row["name"]] = sc.id
        else:
            print("subcategories already exists, skipping...")
            subcategory_map = {s.name: s.id for s in db.query(Subcategory).all()}

        # 7. Products
        if table_empty(db, Product):
            print("Seeding products...")
            product_map = {}
            products_rows = read_csv("products.csv")
            for row in products_rows:
                p = Product(
                    brand_id=brand_map[row["brand"]],
                    subcategory_id=subcategory_map[row["subcategory"]],
                    name=row["name"],
                    slug=row["slug"],
                    source_url=company_url(company_name_by_brand.get(row["brand"]), company_map, companies_rows),
                )
                db.add(p)
                db.flush()
                product_map[row["name"]] = p.id
        else:
            print("products already exists, skipping...")
            product_map = {p.name: p.id for p in db.query(Product).all()}

        # 8. SKUs
        if table_empty(db, Sku):
            print("Seeding SKUs...")
            sku_map = {}
            skus_rows = read_csv("skus.csv")
            for row in skus_rows:
                s = Sku(
                    product_id=product_map[row["product"]],
                    variant=row["variant"],
                    pack_size=float(row["pack_size"]),
                    unit=row["unit"],
                    packaging_type=row["packaging_type"],
                    mrp=float(row["mrp"]),
                    selling_price=float(row["selling_price"]),
                    fat_percent=float(row["fat_percent"]) if row["fat_percent"] else None,
                    protein_percent=float(row["protein_percent"]) if row["protein_percent"] else None,
                    shelf_life_days=int(row["shelf_life_days"]) if row["shelf_life_days"] else None,
                    status=row["status"],
                    source_date=date.today(),
                    last_verified=date.today(),
                )
                db.add(s)
                db.flush()
                # Multiple pack sizes can share (product, variant) — keep ALL of them
                sku_map.setdefault(f"{row['product']}|{row['variant']}", []).append(s.id)

                # Provenance: SKU + its price snapshot sourced from the product's company website
                src_url = company_url(product_company.get(row["product"]), company_map, companies_rows)
                if src_url:
                    s.source_url = src_url
                    db.add(Source(
                        entity_type="sku", entity_id=s.id, source_type="company_website",
                        source_url=src_url,
                        extracted_fact=f"SKU {row['product']} | {row['variant']} | pack={row['pack_size']}{row['unit']} | MRP={row['mrp']}",
                        extraction_date=date.today(), last_verified=date.today(),
                        confidence=SEED_CONFIDENCE,
                    ))
        else:
            print("SKUs already exists, skipping...")
            sku_map = {}
            for s in db.query(Sku).all():
                sku_map.setdefault(f"{s.product.name}|{s.variant}", []).append(s.id)

        # 9. Retailers
        if table_empty(db, Retailer):
            print("Seeding retailers...")
            retailer_map = {}
            retailers_rows = read_csv("retailers.csv")
            for row in retailers_rows:
                r = Retailer(
                    name=row["name"],
                    type=row["type"],
                    parent_company=row["parent_company"] or None,
                    website=row["website"] or None,
                )
                db.add(r)
                db.flush()
                retailer_map[row["name"]] = r.id
        else:
            print("retailers already exists, skipping...")
            retailer_map = {r.name: r.id for r in db.query(Retailer).all()}
        retailer_websites = {r["name"]: (r["website"] or None) for r in read_csv("retailers.csv")}

        # 10. Company-Region mapping (from CSV)
        if table_empty(db, CompanyRegion):
            print("Seeding company_regions...")
            for row in read_csv("company_regions.csv"):
                if row["company"] in company_map and row["region"] in region_map:
                    cr = CompanyRegion(
                        company_id=company_map[row["company"]],
                        region_id=region_map[row["region"]],
                        is_primary=row["is_primary"].lower() == "true",
                    )
                    db.add(cr)
        else:
            print("company_regions already exists, skipping...")

        # 11. Distributors
        if table_empty(db, Distributor):
            print("Seeding distributors...")
            distributor_map = {}
            for row in read_csv("distributors.csv"):
                d = Distributor(
                    name=row["name"],
                    type=row["type"],
                    territory=row["territory"],
                    city=row["city"],
                    state=row["state"],
                    district=row["district"],
                    retailer_count=int(row["retailer_count"]) if row["retailer_count"] else None,
                    channel=row["channel"],
                    website=row["website"] or None,
                    is_active=True,
                )
                db.add(d)
                db.flush()
                distributor_map[row["name"]] = d.id
        else:
            print("distributors already exists, skipping...")
            distributor_map = {d.name: d.id for d in db.query(Distributor).all()}

        # 12. Company-Distributor relationships (from CSV)
        if table_empty(db, CompanyDistributor):
            print("Seeding company_distributors...")
            for row in read_csv("company_distributors.csv"):
                if row["company"] in company_map and row["distributor"] in distributor_map:
                    cd = CompanyDistributor(
                        company_id=company_map[row["company"]],
                        distributor_id=distributor_map[row["distributor"]],
                    )
                    db.add(cd)
        else:
            print("company_distributors already exists, skipping...")

        # 12.5 Provenance for seed companies (description/website evidence)
        if table_empty(db, Source):
            print("Seeding company sources...")
            for row in companies_rows:
                co_id = company_map.get(row["name"])
                if co_id and (row["website"] or row.get("description")):
                    db.add(Source(
                        entity_type="company", entity_id=co_id, source_type="company_website",
                        source_url=row["website"] or None,
                        extracted_fact=(row.get("description") or f"Company profile and product range for {row['name']}")[:2000],
                        extraction_date=date.today(), last_verified=date.today(),
                        confidence=SEED_CONFIDENCE,
                    ))

        # 13. SKU-Retailer relationships (from CSV)
        if table_empty(db, SkuRetailer):
            print("Seeding sku_retailers...")
            sr_count = 0
            for row in read_csv("sku_retailers.csv"):
                sku_key = f"{row['sku_product']}|{row['sku_variant']}"
                sku_ids = sku_map.get(sku_key, [])
                if sku_ids and row["retailer"] in retailer_map and row["region"] in region_map:
                    # A retailer stocking a variant stocks all its pack sizes
                    src_url = company_url(product_company.get(row["sku_product"]), company_map, companies_rows)
                    for sid in sku_ids:
                        sr = SkuRetailer(
                            sku_id=sid,
                            retailer_id=retailer_map[row["retailer"]],
                            region_id=region_map[row["region"]],
                            channel=row["channel"],
                            available=row["available"].lower() == "true",
                            source_date=date.today(),
                        )
                        db.add(sr)
                        sr_count += 1
                        if src_url:
                            db.add(Source(
                                entity_type="sku", entity_id=sid, source_type="retailer_scrape",
                                source_url=retailer_websites.get(row["retailer"]),
                                extracted_fact=f"{row['sku_product']} ({row['sku_variant']}) available at {row['retailer']} in {row['region']}",
                                extraction_date=date.today(), last_verified=date.today(),
                                confidence=SEED_CONFIDENCE,
                            ))
            print(f"  -> {sr_count} sku-retailer links created")
        else:
            print("sku_retailers already exists, skipping...")

        # 14. Price History (from CSV)
        if table_empty(db, PriceHistory):
            print("Seeding price_history...")
            ph_count = 0
            for row in read_csv("price_history.csv"):
                sku_key = f"{row['sku_product']}|{row['sku_variant']}"
                sku_ids = sku_map.get(sku_key, [])
                if sku_ids:
                    # Historical price attaches to the smallest pack (first listed)
                    ph = PriceHistory(
                        sku_id=sku_ids[0],
                        mrp=float(row["mrp"]),
                        selling_price=float(row["selling_price"]),
                        discount_percent=float(row["discount_percent"]) if row["discount_percent"] else None,
                        recorded_date=datetime.strptime(row["recorded_date"], "%Y-%m-%d").date(),
                    )
                    db.add(ph)
                    ph_count += 1
            print(f"  -> {ph_count} price history records created")
        else:
            print("price_history already exists, skipping...")

        db.commit()
        print(f"\nDone! Companies: {len(company_map)}, Brands: {len(brand_map)}, SKUs: {len(sku_map)}, Retailers: {len(retailer_map)}, Distributors: {len(distributor_map)}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
