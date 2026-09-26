"""CSV import API: upload a CSV, validate, preview, then commit into the DB.

Flow:
  POST /api/import/preview  (multipart file + table)  → column check + row errors + sample
  POST /api/import/commit   (same body + confirmed=true) → insert missing rows
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session as SASession

from app.db import SessionLocal
from app.models import (
    Brand, Category, Company, Distributor, PriceHistory, Product,
    Region, Retailer, Sku, SkuRetailer, Subcategory,
)

router = APIRouter()

# Reuse the exact validation rules from the CLI seeder
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from seed import REQUIRED_COLUMNS  # noqa: E402


def _norm_table(table: str) -> str:
    """Accept both 'skus' and 'skus.csv' as table identifiers, return 'skus' style."""
    t = (table or "").strip().lower()
    return t[:-4] if t.endswith(".csv") else t


def _table_key(table: str) -> str:
    """Normalized table name → REQUIRED_COLUMNS key (which keeps the .csv suffix)."""
    return f"{_norm_table(table)}.csv"


def _slugify(text: str) -> str:
    return (text or "").lower().replace(" ", "-").replace("(", "").replace(")", "") \
                        .replace("'", "").replace("&", "and")


def _parse_date(val: str) -> date | None:
    val = (val or "").strip()
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(val: str) -> float | None:
    val = (val or "").strip()
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _to_int(val: str) -> int | None:
    v = _to_float(val)
    return int(v) if v is not None else None


def _to_bool(val: str) -> bool:
    return (val or "").strip().lower() in ("true", "1", "yes", "y")


# ---------------------------------------------------------------- preview

@router.post("/preview")
async def preview_import(
    table: str = Form(...),
    file: UploadFile = File(...),
):
    table = _norm_table(table)
    key = _table_key(table)
    if key not in REQUIRED_COLUMNS:
        allowed = ", ".join(sorted(k[:-4] for k in REQUIRED_COLUMNS))
        raise HTTPException(400, f"Unknown table '{table}'. Allowed: {allowed}")
    required = REQUIRED_COLUMNS[key]

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 5 MB).")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 CSV text.")

    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    except csv.Error as e:
        raise HTTPException(400, f"Invalid CSV: {e}")

    if not rows:
        raise HTTPException(400, "CSV has no data rows.")

    columns = list(rows[0].keys())
    missing = [c for c in required if c not in columns]

    # Row-level required checks (mirrors seed.validate_csv)
    row_errors: list[dict] = []
    for i, row in enumerate(rows, start=2):  # header is line 1
        for col in required:
            if not (row.get(col) or "").strip():
                row_errors.append({"row": i, "column": col, "issue": "empty"})
                if len(row_errors) >= 50:
                    break
        if len(row_errors) >= 50:
            break

    # FK reference checks (only if required columns present)
    fk_errors: list[dict] = []
    if not missing:
        db: SASession = SessionLocal()
        try:
            companies = {c.name for c in db.query(Company).all()}
            brands = {b.name for b in db.query(Brand).all()}
            products = {p.name for p in db.query(Product).all()}
            categories = {c.name for c in db.query(Category).all()}
            subcats = {s.name for s in db.query(Subcategory).all()}
            regions = {r.name for r in db.query(Region).all()}
            retailers = {r.name for r in db.query(Retailer).all()}

            def check(i, val, pool, label):
                if (val or "").strip() and pool and val.strip() not in pool:
                    fk_errors.append({"row": i, "column": label, "value": val.strip(),
                                      "issue": "not found in DB (add it first)"})

            for i, row in enumerate(rows, start=2):
                if table == "brands":
                    check(i, row.get("company"), companies, "company")
                elif table == "products":
                    check(i, row.get("brand"), brands, "brand")
                    check(i, row.get("subcategory"), subcats, "subcategory")
                elif table == "skus":
                    check(i, row.get("product"), products, "product")
                elif table == "subcategories":
                    check(i, row.get("category"), categories, "category")
                elif table == "company_regions":
                    check(i, row.get("company"), companies, "company")
                    check(i, row.get("region"), regions, "region")
                elif table == "sku_retailers":
                    check(i, row.get("retailer"), retailers, "retailer")
                    check(i, row.get("region"), regions, "region")
                elif table == "price_history":
                    pass  # validated at commit time (product+variant must resolve)
                elif table == "companies":
                    check(i, row.get("ownership_type"), companies, "ownership_type")  # informational only
                if len(fk_errors) >= 50:
                    break
        finally:
            db.close()

    return {
        "table": table,
        "filename": file.filename,
        "total_rows": len(rows),
        "columns": columns,
        "required_columns": required,
        "missing_columns": missing,
        "row_errors": row_errors,
        "fk_errors": fk_errors,
        "sample": rows[:5],
        "preview_token": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------- commit

def _resolve_sku(db, product_name: str, variant: str):
    return db.query(Sku).join(Product, Sku.product_id == Product.id).filter(
        Product.name.ilike(product_name.strip()),
        Sku.variant.ilike((variant or "Regular").strip() or "Regular"),
    ).all()


@router.post("/commit")
async def commit_import(
    table: str = Form(...),
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
):
    table = _norm_table(table)
    key = _table_key(table)
    if key not in REQUIRED_COLUMNS:
        allowed = ", ".join(sorted(k[:-4] for k in REQUIRED_COLUMNS))
        raise HTTPException(400, f"Unknown table '{table}'. Allowed: {allowed}")
    required = REQUIRED_COLUMNS[key]

    raw = await file.read()
    try:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except Exception as e:
        raise HTTPException(400, f"Invalid CSV: {e}")
    if not rows:
        raise HTTPException(400, "CSV has no data rows.")

    missing = [c for c in required if c not in rows[0]]
    if missing:
        raise HTTPException(400, f"Missing required columns: {missing}")

    db: SASession = SessionLocal()
    created = updated = skipped = errors = 0
    error_details: list[str] = []
    today = date.today()
    conf = "medium"

    try:
        if table == "skus":
            products = {p.name.lower(): p for p in db.query(Product).all()}
            for i, row in enumerate(rows, start=2):
                try:
                    p = products.get((row.get("product") or "").strip().lower())
                    if p is None:
                        skipped += 1
                        continue
                    variant = (row.get("variant") or "Regular").strip() or "Regular"
                    existing = db.query(Sku).filter(
                        Sku.product_id == p.id, Sku.variant.ilike(variant),
                    ).all()
                    pack = _to_float(row.get("pack_size"))
                    match = None
                    if existing:
                        for s in existing:
                            if pack is not None and s.pack_size is not None and float(s.pack_size) == pack:
                                match = s
                                break
                        if match is None:
                            match = existing[0]
                    if match:
                        # Update prices/facts, keep identity
                        if row.get("mrp"): match.mrp = row["mrp"]
                        if row.get("selling_price"): match.selling_price = row["selling_price"]
                        if row.get("fat_percent"): match.fat_percent = row["fat_percent"]
                        if row.get("protein_percent"): match.protein_percent = row["protein_percent"]
                        match.last_verified = today
                        updated += 1
                    else:
                        db.add(Sku(
                            product_id=p.id,
                            variant=variant,
                            pack_size=pack,
                            unit=row.get("unit") or None,
                            packaging_type=row.get("packaging_type") or None,
                            mrp=row.get("mrp") or None,
                            selling_price=row.get("selling_price") or None,
                            fat_percent=row.get("fat_percent") or None,
                            protein_percent=row.get("protein_percent") or None,
                            shelf_life_days=_to_int(row.get("shelf_life_days")),
                            status=row.get("status") or "active",
                            source_url=None,  # set below from company chain
                            source_date=today,
                            last_verified=today,
                            confidence=conf,
                        ))
                        created += 1
                except Exception as e:
                    errors += 1
                    if len(error_details) < 20:
                        error_details.append(f"row {i}: {e}")

        elif table == "brands":
            companies = {c.name.lower(): c for c in db.query(Company).all()}
            for i, row in enumerate(rows, start=2):
                try:
                    c = companies.get((row.get("company") or "").strip().lower())
                    if c is None:
                        skipped += 1
                        continue
                    name = (row.get("brand_name") or "").strip()
                    exists = db.query(Brand).filter(
                        Brand.company_id == c.id, Brand.name.ilike(name)).first()
                    if exists:
                        updated += 1
                        continue
                    db.add(Brand(company_id=c.id, name=name, slug=row.get("brand_slug") or _slugify(name)))
                    created += 1
                except Exception as e:
                    errors += 1
                    if len(error_details) < 20:
                        error_details.append(f"row {i}: {e}")

        elif table == "products":
            brands = {b.name.lower(): b for b in db.query(Brand).all()}
            subcats = {s.name.lower(): s for s in db.query(Subcategory).all()}
            for i, row in enumerate(rows, start=2):
                try:
                    b = brands.get((row.get("brand") or "").strip().lower())
                    sc = subcats.get((row.get("subcategory") or "").strip().lower())
                    if b is None or sc is None:
                        skipped += 1
                        continue
                    name = (row.get("name") or "").strip()
                    exists = db.query(Product).filter(
                        Product.brand_id == b.id,
                        Product.subcategory_id == sc.id,
                        Product.name.ilike(name)).first()
                    if exists:
                        updated += 1
                        continue
                    db.add(Product(brand_id=b.id, subcategory_id=sc.id, name=name,
                                   slug=row.get("slug") or _slugify(name),
                                   description=row.get("description") or None))
                    created += 1
                except Exception as e:
                    errors += 1
                    loop_i = i
                    if len(error_details) < 20:
                        error_details.append(f"row {loop_i}: {e}")

        elif table == "sku_retailers":
            retailers = {r.name.lower(): r for r in db.query(Retailer).all()}
            regions = {r.name.lower(): r for r in db.query(Region).all()}
            for i, row in enumerate(rows, start=2):
                try:
                    sku_list = _resolve_sku(db, row.get("sku_product") or "", row.get("sku_variant") or "")
                    r = retailers.get((row.get("retailer") or "").strip().lower())
                    reg = regions.get((row.get("region") or "").strip().lower())
                    if not sku_list or r is None or reg is None:
                        skipped += 1
                        continue
                    # Link ALL packs of this (product, variant) — matches seed.py behaviour
                    for sku in sku_list:
                        exists = db.query(SkuRetailer).filter(
                            SkuRetailer.sku_id == sku.id,
                            SkuRetailer.retailer_id == r.id,
                            SkuRetailer.region_id == reg.id).first()
                        if exists:
                            updated += 1
                            continue
                        db.add(SkuRetailer(
                            sku_id=sku.id, retailer_id=r.id, region_id=reg.id,
                            channel=row.get("channel") or None,
                            available=_to_bool(row.get("available")),
                            source_url=None,
                            source_date=today,
                        ))
                        created += 1
                except Exception as e:
                    errors += 1
                    if len(error_details) < 20:
                        error_details.append(f"row {i}: {e}")

        elif table == "price_history":
            for i, row in enumerate(rows, start=2):
                try:
                    sku_list = _resolve_sku(db, row.get("sku_product") or "", row.get("sku_variant") or "")
                    if not sku_list:
                        skipped += 1
                        continue
                    d = _parse_date(row.get("recorded_date"))
                    if d is None:
                        errors += 1
                        if len(error_details) < 20:
                            error_details.append(f"row {i}: bad date '{row.get('recorded_date')}'")
                        continue
                    mrp = _to_float(row.get("mrp"))
                    sell = _to_float(row.get("selling_price"))
                    for sku in sku_list:  # all packs
                        exists = db.query(PriceHistory).filter(
                            PriceHistory.sku_id == sku.id,
                            PriceHistory.recorded_date == d).first()
                        if exists:
                            exists.mrp = mrp if mrp is not None else exists.mrp
                            exists.selling_price = sell if sell is not None else exists.selling_price
                            updated += 1
                            continue
                        disc = round((1 - sell / mrp) * 100, 2) if (mrp and sell and mrp > 0) else None
                        db.add(PriceHistory(
                            sku_id=sku.id, mrp=mrp, selling_price=sell,
                            discount_percent=disc,
                            recorded_date=d,
                        ))
                        created += 1
                except Exception as e:
                    errors += 1
                    if len(error_details) < 20:
                        error_details.append(f"row {i}: {e}")

        elif table == "distributors":
            for i, row in enumerate(rows, start=2):
                try:
                    name = (row.get("name") or "").strip()
                    if not name:
                        skipped += 1
                        continue
                    exists = db.query(Distributor).filter(Distributor.name.ilike(name)).first()
                    if exists:
                        updated += 1
                        continue
                    db.add(Distributor(
                        name=name,
                        type=row.get("type") or None,
                        territory=row.get("territory") or None,
                        state=row.get("state") or None,
                        city=row.get("city") or None,
                        district=row.get("district") or None,
                        channel=row.get("channel") or None,
                        is_active=True,
                        confidence=conf,
                    ))
                    created += 1
                except Exception as handler_e:
                    errors += 1
                    if len(error_details) < 20:
                        error_details.append(f"row {i}: {handler_e}")

        else:
            # companies / subcategories / regions / retailers / etc.
            raise HTTPException(400, f"Commit for '{table}' is not supported yet. "
                                     f"Supported: brands, products, skus, sku_retailers, price_history, distributors.")

        if dry_run:
            db.rollback()
            skipped = skipped  # counts still meaningful
        else:
            db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Import failed, rolled back: {e}")
    finally:
        db.close()

    return {
        "table": table,
        "dry_run": dry_run,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "error_details": error_details,
        "status": "rolled_back" if dry_run else "committed",
    }
