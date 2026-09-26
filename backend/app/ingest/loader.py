"""Upsert RawPayload into DB with provenance (sources), diffs (change_events), review_queue."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import (
    Brand, Category, ChangeEvent, Company, CompanyDistributor, CompanyRegion,
    Distributor, PriceHistory, Product, Region, ReviewQueue, Sku, Source, Subcategory,
)
from app.ingest.normalize import (
    RawPayload, detect_category, detect_subcategory, fuzzy_in, norm_name, slugify,
)


@dataclass
class LoadStats:
    company: str = ""
    company_updated: int = 0
    brands_created: int = 0
    brands_linked: int = 0
    products_created: int = 0
    products_linked: int = 0
    skus_created: int = 0
    skus_updated: int = 0
    regions_created: int = 0
    region_links: int = 0
    distributors_created: int = 0
    distributor_links: int = 0
    price_records: int = 0
    change_events: int = 0
    review_items: int = 0
    sources: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "errors"}
        d["errors"] = list(self.errors)
        return d


class Loader:
    def __init__(self, db: Session, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run

    # --- provenance helpers ---

    def add_source(self, entity_type: str, entity_id: int, payload: RawPayload,
                   fact: str, confidence: Optional[str] = None) -> None:
        s = Source(
            entity_type=entity_type,
            entity_id=entity_id,
            source_type=payload.source_type,
            source_url=payload.source_url,
            extracted_fact=fact[:2000],
            extraction_date=date.today(),
            last_verified=date.today(),
            confidence=confidence or payload.confidence,
        )
        self.db.add(s)

    def add_change(self, entity_type: str, entity_id: int, event_type: str,
                   field_name: Optional[str], old: Any, new: Any,
                   description: str, source_url: Optional[str]) -> None:
        ev = ChangeEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            field_name=field_name,
            old_value=None if old is None else str(old),
            new_value=None if new is None else str(new),
            description=description,
            source_url=source_url,
        )
        self.db.add(ev)

    def add_review(self, entity_type: str, entity_id: Optional[int], action: str,
                   data: dict, notes: str, payload: RawPayload) -> None:
        item = ReviewQueue(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,  # new | update | merge | ambiguous
            status="pending",
            data=json.dumps(data, ensure_ascii=False, default=str),
            notes=notes[:2000],
        )
        self.db.add(item)

    # --- lookups ---

    def get_company(self, slug: str) -> Optional[Company]:
        return self.db.query(Company).filter(Company.slug == slug).first()

    def _region_by_name(self, name: str) -> Optional[Region]:
        n = (name or "").strip()
        if not n:
            return None
        r = self.db.query(Region).filter(Region.name.ilike(n)).first()
        if r:
            return r
        # fuzzy over known regions
        regions = self.db.query(Region).all()
        match = fuzzy_in(n, [x.name for x in regions])
        if match:
            return self.db.query(Region).filter(Region.name == match).first()
        return None

    def _ensure_region(self, name: str, stats: LoadStats) -> Optional[Region]:
        r = self._region_by_name(name)
        if r:
            return r
        # Create as state-level orphan (no parent) — admin can fix via review if wrong.
        level = "state"
        low = name.lower()
        if low in ("north", "south", "east", "west", "central"):
            level = "region"
        r = Region(name=name.strip(), level=level, parent_id=None)
        self.db.add(r)
        self.db.flush()
        stats.regions_created += 1
        return r

    def _category_id(self, name: str) -> Optional[int]:
        c = self.db.query(Category).filter(Category.name.ilike(name.strip())).first()
        return c.id if c else None

    def _ensure_subcategory(self, name: str, category_hint: Optional[str],
                            stats: LoadStats) -> Optional[int]:
        name = (name or "").strip()
        if not name:
            return None
        sc = self.db.query(Subcategory).filter(Subcategory.name.ilike(name)).first()
        if sc:
            return sc.id
        # Try fuzzy against existing subcategory names
        all_sc = [x.name for x in self.db.query(Subcategory).all()]
        match = fuzzy_in(name, all_sc)
        if match:
            sc = self.db.query(Subcategory).filter(Subcategory.name == match).first()
            return sc.id if sc else None
        # New subcategory — attach to category (from hint or detect from name)
        cat_name = category_hint or detect_category(name)
        cat_id = self._category_id(cat_name) if cat_name else None
        if cat_id is None:
            # Can't place it — leave to review_queue (caller decides)
            return None
        sc = Subcategory(category_id=cat_id, name=name, slug=slugify(name))
        self.db.add(sc)
        self.db.flush()
        return sc.id

    def _ensure_brand(self, company: Company, name: str, source_url: Optional[str],
                      stats: LoadStats) -> Optional[Brand]:
        name = (name or "").strip()
        if not name:
            return None
        b = self.db.query(Brand).filter(Brand.company_id == company.id,
                                         Brand.name.ilike(name)).first()
        if b:
            stats.brands_linked += 1
            return b
        # Fuzzy within company brands (strict: exact normalized match only)
        existing = [x.name for x in self.db.query(Brand).filter(Brand.company_id == company.id).all()]
        match = fuzzy_in(name, existing, strict=True)
        if match:
            b = self.db.query(Brand).filter(Brand.company_id == company.id,
                                             Brand.name == match).first()
            stats.brands_linked += 1
            return b
        b = Brand(company_id=company.id, name=name, slug=slugify(name), source_url=source_url)
        self.db.add(b)
        self.db.flush()
        stats.brands_created += 1
        self.add_source("brand", b.id, self._current_payload, f"Brand '{name}'", "medium")
        return b

    # Set during load for add_source convenience
    _current_payload: Optional[RawPayload] = None

    def _ensure_product(self, brand: Brand, name: str, subcategory_id: Optional[int],
                        description: Optional[str], source_url: Optional[str],
                        stats: LoadStats) -> Optional[Product]:
        name = (name or "").strip()
        if not name or subcategory_id is None or brand is None:
            return None
        p = self.db.query(Product).filter(
            Product.brand_id == brand.id,
            Product.subcategory_id == subcategory_id,
            Product.name.ilike(name),
        ).first()
        if p:
            stats.products_linked += 1
            return p
        # Fuzzy within brand products
        existing = [x.name for x in self.db.query(Product).filter(Product.brand_id == brand.id).all()]
        match = fuzzy_in(name, existing)
        if match:
            p = self.db.query(Product).filter(Product.brand_id == brand.id,
                                              Product.name == match).first()
            stats.products_linked += 1
            return p
        p = Product(brand_id=brand.id, subcategory_id=subcategory_id, name=name,
                    slug=slugify(name), description=description, source_url=source_url)
        self.db.add(p)
        self.db.flush()
        stats.products_created += 1
        self.add_source("product", p.id, self._current_payload, f"Product '{name}'", "medium")
        return p

    def _ensure_sku(self, product: Product, raw, stats: LoadStats):
        """Upsert SKU keyed by (product_id, variant, pack_size, unit)."""
        variant = (raw.variant or "Regular").strip() or "Regular"
        existing = self.db.query(Sku).filter(
            Sku.product_id == product.id,
            Sku.variant.ilike(variant),
        ).all()
        # Disambiguate by pack if multiple
        match = None
        if len(existing) == 1:
            match = existing[0]
        elif existing and raw.pack_size is not None:
            for s in existing:
                if s.pack_size is not None and float(s.pack_size) == float(raw.pack_size):
                    match = s
                    break
            if match is None:
                match = existing[0]  # best effort first with same variant
        elif existing:
            match = existing[0]

        today = date.today()
        if match:
            changed = False
            old_mrp = float(match.mrp) if match.mrp is not None else None
            old_sell = float(match.selling_price) if match.selling_price is not None else None
            new_mrp = float(raw.mrp) if raw.mrp is not None else old_mrp
            new_sell = float(raw.selling_price) if raw.selling_price is not None else old_sell

            if raw.mrp is not None and old_mrp is not None and abs(new_mrp - old_mrp) > 0.001:
                self.add_change("sku", match.id, "PRICE_CHANGED", "mrp", old_mrp, new_mrp,
                                f"MRP {old_mrp} → {new_mrp} for {product.name} {variant}",
                                raw.source_url or self._current_payload.source_url)
                stats.change_events += 1
                changed = True
            if raw.selling_price is not None and old_sell is not None and abs(new_sell - old_sell) > 0.001:
                self.add_change("sku", match.id, "PRICE_CHANGED", "selling_price", old_sell, new_sell,
                                f"Price {old_sell} → {new_sell} for {product.name} {variant}",
                                raw.source_url or self._current_payload.source_url)
                stats.change_events += 1
                changed = True

            if raw.mrp is not None:
                match.mrp = raw.mrp
            if raw.selling_price is not None:
                match.selling_price = raw.selling_price
            if raw.pack_size is not None:
                match.pack_size = raw.pack_size
            if raw.unit:
                match.unit = raw.unit
            if raw.flavour:
                match.flavour = raw.flavour
            if raw.packaging_type:
                match.packaging_type = raw.packaging_type
            if raw.fat_percent is not None:
                match.fat_percent = raw.fat_percent
            if raw.protein_percent is not None:
                match.protein_percent = raw.protein_percent
            match.last_verified = today
            match.source_date = today
            match.source_url = raw.source_url or match.source_url
            stats.skus_updated += 1
            if changed:
                # Price history snapshot when price moved
                if raw.mrp is not None or raw.selling_price is not None:
                    self._add_price_snapshot(match, raw, stats)
            return match

        s = Sku(
            product_id=product.id,
            variant=variant,
            pack_size=raw.pack_size,
            unit=raw.unit,
            packaging_type=raw.packaging_type,
            mrp=raw.mrp,
            selling_price=raw.selling_price,
            fat_percent=raw.fat_percent,
            protein_percent=raw.protein_percent,
            shelf_life_days=raw.shelf_life_days,
            flavour=raw.flavour,
            status=raw.status or "active",
            source_url=raw.source_url,
            source_date=today,
            last_verified=today,
            confidence=self._current_payload.confidence,
        )
        self.db.add(s)
        self.db.flush()
        stats.skus_created += 1
        self.add_source("sku", s.id, self._current_payload,
                        f"SKU {product.name} | {variant} | pack={raw.pack_size}{raw.unit or ''}",
                        self._current_payload.confidence)
        if raw.mrp is not None or raw.selling_price is not None:
            self._add_price_snapshot(s, raw, stats)
        # Announce new product/SKU
        self.add_change("sku", s.id, "SKU_ADDED", None, None,
                        f"{product.name} {variant}",
                        f"New SKU discovered: {product.name} ({variant})",
                        raw.source_url or self._current_payload.source_url)
        stats.change_events += 1
        return s

    def _add_price_snapshot(self, sku: Sku, raw, stats: LoadStats) -> None:
        today = date.today()
        # Avoid duplicate same-day snapshot
        existing = self.db.query(PriceHistory).filter(
            PriceHistory.sku_id == sku.id,
            PriceHistory.recorded_date == today,
        ).first()
        mrp = float(raw.mrp) if raw.mrp is not None else (float(sku.mrp) if sku.mrp is not None else None)
        sell = float(raw.selling_price) if raw.selling_price is not None else (
            float(sku.selling_price) if sku.selling_price is not None else None)
        if existing:
            existing.mrp = mrp if mrp is not None else existing.mrp
            existing.selling_price = sell if sell is not None else existing.selling_price
            if mrp and sell and mrp > 0:
                existing.discount_percent = round((1 - sell / mrp) * 100, 2)
            return
        discount = None
        if mrp and sell and mrp > 0:
            discount = round((1 - sell / mrp) * 100, 2)
        ph = PriceHistory(
            sku_id=sku.id,
            mrp=mrp,
            selling_price=sell,
            discount_percent=discount,
            source_url=raw.source_url or getattr(self._current_payload, "source_url", None),
            recorded_date=today,
        )
        self.db.add(ph)
        stats.price_records += 1

    # --- main load ---

    def load(self, payload: RawPayload) -> LoadStats:
        stats = LoadStats(company=payload.company_slug)
        self._current_payload = payload
        company = self.get_company(payload.company_slug)
        if not company:
            stats.errors.append(f"Company not found in DB: {payload.company_slug}")
            self.add_review("company", None, "new",
                            {"slug": payload.company_slug, "source_url": payload.source_url,
                             "description": payload.description},
                            f"Company '{payload.company_slug}' not in DB; payload received", payload)
            stats.review_items += 1
            return stats

        # 1. Company fields
        if payload.description and payload.description.strip():
            old = (company.description or "").strip()
            new = payload.description.strip()
            if new and new != old:
                if old:
                    self.add_change("company", company.id, "FIELD_CHANGED", "description",
                                    old[:500], new[:500],
                                    "Company description updated from source",
                                    payload.source_url)
                    stats.change_events += 1
                company.description = new
                company.source_url = payload.source_url
                company.confidence = payload.confidence
                company.source_date = date.today()
                stats.company_updated += 1
                self.add_source("company", company.id, payload,
                                f"Description ({len(new)} chars)", payload.confidence)
                stats.sources += 1
        if payload.parent_company and payload.parent_company.strip():
            if (company.parent_company or "").strip() != payload.parent_company.strip():
                company.parent_company = payload.parent_company.strip()
                stats.company_updated += 1
        if payload.is_listed is not None and payload.is_listed != company.is_listed:
            self.add_change("company", company.id, "FIELD_CHANGED", "is_listed",
                            company.is_listed, payload.is_listed,
                            "Listing status updated from source", payload.source_url)
            company.is_listed = payload.is_listed
            stats.change_events += 1
            stats.company_updated += 1
        if payload.is_global is not None and payload.is_global != company.is_global:
            company.is_global = payload.is_global
            stats.company_updated += 1

        # 2. Brands
        for rb in payload.brands:
            try:
                self._ensure_brand(company, rb.name, rb.source_url or payload.source_url, stats)
            except Exception as e:
                stats.errors.append(f"brand '{rb.name}': {e}")

        # 3. Products + SKUs (each product needs brand + subcategory)
        # Build a brand lookup for products that name a brand
        for rp in payload.products:
            try:
                brand = None
                if rp.brand:
                    brand = self._ensure_brand(company, rp.brand, rp.source_url or payload.source_url, stats)
                if brand is None:
                    # Take first company brand as fallback? Better: skip with review.
                    existing_brands = self.db.query(Brand).filter(Brand.company_id == company.id).all()
                    if len(existing_brands) == 1:
                        brand = existing_brands[0]
                    else:
                        self.add_review("product", None, "ambiguous",
                                        {"name": rp.name, "brand": rp.brand,
                                         "source_url": rp.source_url or payload.source_url},
                                        f"Cannot attach product '{rp.name}' — brand missing/ambiguous",
                                        payload)
                        stats.review_items += 1
                        continue

                sub_name = rp.subcategory or detect_subcategory(rp.name) or detect_subcategory(rp.description or "")
                cat_hint = rp.category or detect_category(rp.name) or detect_category(sub_name or "")
                sub_id = None
                if sub_name:
                    sub_id = self._ensure_subcategory(sub_name, cat_hint, stats)
                if sub_id is None:
                    self.add_review("product", None, "ambiguous",
                                    {"name": rp.name, "subcategory": sub_name,
                                     "category": cat_hint,
                                     "source_url": rp.source_url or payload.source_url},
                                    f"Product '{rp.name}' has no matching subcategory in taxonomy",
                                    payload)
                    stats.review_items += 1
                    continue

                product = self._ensure_product(brand, rp.name, sub_id, rp.description,
                                               rp.source_url or payload.source_url, stats)
                if product is None:
                    stats.errors.append(f"product '{rp.name}' could not be created")
            except Exception as e:
                stats.errors.append(f"product '{rp.name}': {e}")

        # 4. SKUs (raw.skus reference product by name; brand optional)
        for raw_sku in payload.skus:
            try:
                brand = None
                if raw_sku.brand:
                    brand = self._ensure_brand(company, raw_sku.brand, raw_sku.source_url or payload.source_url, stats)
                # Find product by name (within company brands if brand set)
                pname = raw_sku.product
                q = self.db.query(Product).join(Brand, Product.brand_id == Brand.id).filter(
                    Brand.company_id == company.id, Product.name.ilike(pname)
                )
                product = q.first()
                if product is None:
                    # Fuzzy product name match
                    all_p = [x.name for x in self.db.query(Product)
                             .join(Brand, Product.brand_id == Brand.id)
                             .filter(Brand.company_id == company.id).all()]
                    m = fuzzy_in(pname, all_p)
                    if m:
                        product = self.db.query(Product).join(Brand, Product.brand_id == Brand.id).filter(
                            Brand.company_id == company.id, Product.name == m
                        ).first()
                if product is None:
                    # Try create product by detecting subcategory from name
                    sub_name = detect_subcategory(pname) or detect_subcategory(raw_sku.flavour or "")
                    cat_hint = detect_category(pname)
                    sub_id = self._ensure_subcategory(sub_name, cat_hint, stats) if sub_name else None
                    if brand is None:
                        eb = self.db.query(Brand).filter(Brand.company_id == company.id).all()
                        if len(eb) == 1:
                            brand = eb[0]
                    if brand is not None and sub_id is not None:
                        product = self._ensure_product(brand, pname, sub_id, None,
                                                       raw_sku.source_url or payload.source_url, stats)
                    else:
                        self.add_review("sku", None, "ambiguous",
                                        {"product": pname, "variant": raw_sku.variant,
                                         "source_url": raw_sku.source_url or payload.source_url},
                                        f"SKU product '{pname}' not found and could not be created",
                                        payload)
                        stats.review_items += 1
                        continue
                self._ensure_sku(product, raw_sku, stats)
            except Exception as e:
                stats.errors.append(f"sku '{raw_sku.product}': {e}")

        # 5. Regions → company_regions
        for rname in payload.regions:
            try:
                region = self._ensure_region(rname, stats)
                if region is None:
                    continue
                link = self.db.query(CompanyRegion).filter(
                    CompanyRegion.company_id == company.id,
                    CompanyRegion.region_id == region.id,
                ).first()
                if link is None:
                    self.db.add(CompanyRegion(company_id=company.id, region_id=region.id,
                                              source_url=payload.source_url))
                    stats.region_links += 1
                    self.add_source("company_region", company.id, payload,
                                    f"Presence in region '{region.name}'", payload.confidence)
                    stats.sources += 1
            except Exception as e:
                stats.errors.append(f"region '{rname}': {e}")

        # 6. Distributors
        for rd in payload.distributors:
            try:
                d = self.db.query(Distributor).filter(Distributor.name.ilike(rd.name.strip())).first()
                if d is None:
                    existing = [x.name for x in self.db.query(Distributor).all()]
                    m = fuzzy_in(rd.name, existing)
                    if m:
                        d = self.db.query(Distributor).filter(Distributor.name == m).first()
                if d is None:
                    d = Distributor(
                        name=rd.name.strip(),
                        type=rd.type,
                        territory=rd.territory,
                        state=rd.state,
                        city=rd.city,
                        district=rd.district,
                        channel=rd.channel,
                        website=rd.website,
                        source_url=rd.source_url or payload.source_url,
                        is_active=True,
                        confidence=payload.confidence,
                    )
                    self.db.add(d)
                    self.db.flush()
                    stats.distributors_created += 1
                    self.add_source("distributor", d.id, payload,
                                    f"Distributor '{d.name}'", payload.confidence)
                    stats.sources += 1
                # Link to company
                link = self.db.query(CompanyDistributor).filter(
                    CompanyDistributor.company_id == company.id,
                    CompanyDistributor.distributor_id == d.id,
                ).first()
                if link is None:
                    self.db.add(CompanyDistributor(company_id=company.id, distributor_id=d.id,
                                                   source_url=payload.source_url))
                    stats.distributor_links += 1
            except Exception as e:
                stats.errors.append(f"distributor '{rd.name}': {e}")

        # 7. Facts → sources on company (for AR free-form evidence)
        for fact in payload.facts[:20]:
            self.add_source("company", company.id, payload, fact, payload.confidence)
            stats.sources += 1

        if self.dry_run:
            self.db.rollback()
        else:
            self.db.commit()
        return stats
