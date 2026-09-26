"""Website Scanner API: scan any URL on demand, report results, optionally save to DB.

Endpoints:
  POST /api/scan/start  {url}  → start background scan job
  GET  /api/scan/status        → poll job (log + report when done)
  POST /api/scan/save          → persist a finished scan into companies/brands/products/skus
"""
from __future__ import annotations

import threading
import traceback
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from app.db import SessionLocal
from app.models import Brand, Company, Product, Sku, Source, Subcategory
from app.ingest.scan_any import scan_website

router = APIRouter()


# ---------------------------------------------------------------- job state

class ScanState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.running = False
        self.url: str | None = None
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.log: list[dict] = []
        self.report: dict | None = None
        self.error: str | None = None


_scan = ScanState()
_scan_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(level: str, message: str):
    _scan.log.append({"time": _now(), "level": level, "message": message})
    if len(_scan.log) > 300:
        del _scan.log[: len(_scan.log) - 300]


def _run_scan(url: str):
    try:
        _log("info", f"Scanning {url} …")
        report = scan_website(url)
        _scan.report = report
        _log("info", f"Crawled {report['pages_crawled']} pages.")
        if report["products"]:
            _log("success", f"Found {len(report['products'])} products, {len(report['brands'])} brands.")
        else:
            _log("info", "No products found — see notes in report.")
        if report["errors"]:
            for e in report["errors"][:5]:
                _log("error", e)
        _log("info", f"Done. Confidence: {report['confidence']}.")
    except Exception as e:
        _scan.error = str(e)
        _log("error", f"Scan failed: {e}")
        _log("error", traceback.format_exc(limit=5))
    finally:
        _scan.running = False
        _scan.finished_at = _now()


# ---------------------------------------------------------------- schemas

class ScanStartRequest(BaseModel):
    url: str


class ScanSaveRequest(BaseModel):
    url: str
    company_name: str | None = None
    ownership_type: str | None = None
    headquarter_region: str | None = None


# ---------------------------------------------------------------- endpoints

@router.post("/start")
def start_scan(req: ScanStartRequest):
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(422, "URL is required.")
    if _scan.running:
        raise HTTPException(409, "A scan is already running — poll /api/scan/status.")

    with _scan_lock:
        if _scan.running:
            raise HTTPException(409, "A scan is already running.")
        _scan.reset()
        _scan.running = True
        _scan.url = url
        _scan.started_at = _now()
        threading.Thread(target=_run_scan, args=(url,), daemon=True).start()

    return {"started": True, "url": url}


@router.get("/status")
def scan_status():
    return {
        "running": _scan.running,
        "url": _scan.url,
        "started_at": _scan.started_at,
        "finished_at": _scan.finished_at,
        "error": _scan.error,
        "log": _scan.log,
        "report": _scan.report,
    }


@router.post("/save")
def save_scan(req: ScanSaveRequest):
    """Persist a finished scan report into the DB as a new/updated company."""
    report = _scan.report
    if report is None:
        raise HTTPException(400, "No scan report available. Run a scan first.")
    if report.get("scanned_url") != (req.url or "").strip() and req.url:
        raise HTTPException(409, "Report URL mismatch — scan a fresh URL first.")

    name = (req.company_name or report.get("company_name") or report.get("host") or "").strip()
    if not name:
        raise HTTPException(422, "Could not determine a company name — pass company_name explicitly.")

    # Build slug
    slug = name.lower().replace(" ", "-").replace("(", "").replace(")", "") \
                     .replace("'", "").replace("&", "and")[:80]

    db = SessionLocal()
    created = {"company": False, "brands": 0, "products": 0, "skus": 0}
    try:
        # 1. Company (match by slug, then by website, else create)
        company = db.query(Company).filter(Company.slug == slug).first()
        if company is None and report.get("scanned_url"):
            company = db.query(Company).filter(
                Company.website.ilike(f"%{report['host']}%")).first()
        if company is None:
            company = Company(
                name=name,
                slug=slug,
                website=report.get("scanned_url"),
                description=report.get("description"),
                source_url=report.get("scanned_url"),
                source_date=date.today(),
                confidence="medium",
            )
            db.add(company)
            db.flush()
            created["company"] = True

        # Update description if empty and scan found one
        if not company.description and report.get("description"):
            company.description = report["description"][:4000]
            company.source_date = date.today()

        def add_source(entity_type: str, entity_id: int, fact: str):
            db.add(Source(
                entity_type=entity_type,
                entity_id=entity_id,
                source_type="website_scan",
                source_url=report.get("scanned_url"),
                extracted_fact=fact[:2000],
                extraction_date=date.today(),
                last_verified=date.today(),
                confidence="medium",
            ))

        if created["company"]:
            add_source("company", company.id, f"Company discovered via website scan of {report['host']}")

        # 2. Brands
        brand_map: dict[str, Brand] = {}
        for bname in report.get("brands", []):
            b = db.query(Brand).filter(
                Brand.company_id == company.id, Brand.name.ilike(bname.strip())).first()
            if b is None:
                b = Brand(company_id=company.id, name=bname.strip(),
                          slug=bname.strip().lower().replace(" ", "-")[:80],
                          source_url=report.get("scanned_url"))
                db.add(b)
                db.flush()
                created["brands"] += 1
                add_source("brand", b.id, f"Brand '{b.name}' found on website")
            brand_map[b.name.lower()] = b
            db.flush()

        # 3. Products + SKUs
        for p in report.get("products", []):
            pname = (p.get("name") or "").strip()
            if not pname:
                continue
            # Brand: named on product, else first company brand, else create one
            brand = None
            if p.get("brand"):
                brand = brand_map.get(p["brand"].lower()) or \
                        db.query(Brand).filter(
                            Brand.company_id == company.id,
                            Brand.name.ilike(p["brand"].strip())).first()
            if brand is None:
                brand = db.query(Brand).filter(
                    Brand.company_id == company.id).first()
            if brand is None:
                brand = Brand(company_id=company.id, name=name,
                              slug=slug, source_url=report.get("scanned_url"))
                db.add(brand)
                db.flush()
                brand_map[brand.name.lower()] = brand

            # Subcategory: scan hint, else leave as None-able (need one) → use generic
            subcat = db.query(Subcategory).filter(
                Subcategory.name.ilike(p.get("subcategory") or "")).first()
            if subcat is None:
                subcat = db.query(Subcategory).filter(
                    Subcategory.name.ilike("Other")).first()
            if subcat is None:
                # last resort: first subcategory in DB
                subcat = db.query(Subcategory).first()
            if subcat is None:
                raise HTTPException(500, "No subcategories exist in taxonomy — seed first.")

            existing = db.query(Product).filter(
                Product.brand_id == brand.id,
                Product.subcategory_id == subcat.id,
                Product.name.ilike(pname)).first()
            if existing:
                product = existing
            else:
                product = Product(
                    brand_id=brand.id,
                    subcategory_id=subcat.id,
                    name=pname,
                    slug=pname.lower().replace(" ", "-")[:100],
                    description=p.get("description"),
                    source_url=p.get("source_url") or report.get("scanned_url"),
                )
                db.add(product)
                db.flush()
                created["products"] += 1
                add_source("product", product.id, f"Product '{pname}' found on website")

            # SKU if price or pack info present
            if p.get("mrp") is not None or p.get("pack_size") is not None:
                variant = "Regular"
                sku = db.query(Sku).filter(
                    Sku.product_id == product.id,
                    Sku.variant.ilike(variant)).first()
                if sku is None:
                    sku = Sku(
                        product_id=product.id,
                        variant=variant,
                        pack_size=p.get("pack_size"),
                        unit=p.get("unit"),
                        mrp=p.get("mrp"),
                        selling_price=p.get("selling_price"),
                        status="active",
                        source_url=p.get("source_url") or report.get("scanned_url"),
                        source_date=date.today(),
                        last_verified=date.today(),
                        confidence="medium",
                    )
                    db.add(sku)
                    db.flush()
                    created["skus"] += 1
                    add_source("sku", sku.id,
                               f"SKU {pname} ({variant}) pack={p.get('pack_size') or '?'}{p.get('unit') or ''} mrp={p.get('mrp') or '?'}")

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except ValidationError as e:
        db.rollback()
        raise HTTPException(422, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Save failed, rolled back: {e}")
    finally:
        db.close()

    return {"saved": True, "company": name, **created}
