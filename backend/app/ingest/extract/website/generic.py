"""Website extractor: config-driven generic adapter + rules."""
from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from app.ingest.config import CompanyCfg
from app.ingest.fetch.http import HttpClient, FetchError
from app.ingest.fetch.pages import (
    abs_url, discover_sitemap_urls, filter_urls, same_host_urls,
)
from app.ingest.normalize import (
    RawBrand, RawDistributor, RawPayload, RawProduct, RawSku,
    detect_category, detect_subcategory, parse_pack, parse_price,
)

# Path tokens we care about when filtering sitemap URLs for products/brands.
PRODUCT_TOKENS = (
    "product", "products", "brand", "brands", "our-", "catalog", "range",
    "milk", "dairy", "cheese", "ghee", "curd", "paneer", "ice-cream", "yogurt",
    "butter", "powder", "sweet",
)
BRAND_TOKENS = ("brand", "brands")
ABOUT_TOKENS = ("about", "who-we-are", "company", "profile", "overview")
DISTRIBUTOR_TOKENS = ("distributor", "dealer", "partner", "channel", "stockist", "retailer")
SKIP_TOKENS = ("career", "job", "press", "media", "blog", "news", "contact", "privacy",
               "terms", "policy", "sitemap", "login", "cart", "checkout", "video", "gallery")

MAX_PAGES = 40  # hard cap per company run


def _visible_text(soup: BeautifulSoup, limit: int = 4000) -> str:
    for t in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        t.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:limit]


def _extract_jsonld_products(soup: BeautifulSoup) -> list[dict]:
    out = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            types = t if isinstance(t, list) else [t]
            if any(str(x).lower() in ("product", "someproducts") for x in types):
                out.append(item)
            # graph nesting
            g = item.get("@graph")
            if isinstance(g, list):
                for sub in g:
                    if isinstance(sub, dict) and str(sub.get("@type", "")).lower() == "product":
                        out.append(sub)
    return out


def _product_from_jsonld(item: dict, url: str) -> tuple[Optional[RawProduct], Optional[RawSku]]:
    name = item.get("name")
    if not name or not isinstance(name, str):
        return None, None
    desc = item.get("description") or None
    if isinstance(desc, str):
        desc = " ".join(desc.split())[:2000]
    brand_raw = item.get("brand")
    brand_name = None
    if isinstance(brand_raw, dict):
        brand_name = brand_raw.get("name")
    elif isinstance(brand_raw, str):
        brand_name = brand_raw
    offers = item.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    mrp = sell = None
    if isinstance(offers, dict):
        price = offers.get("price") or offers.get("lowPrice")
        high = offers.get("highPrice") or offers.get("priceCurrency")
        try:
            if price is not None:
                sell = float(price)
        except (TypeError, ValueError):
            sell = None
        # priceSpecification may hold mrp
        ps = offers.get("priceSpecification")
        if isinstance(ps, dict):
            try:
                if ps.get("price") is not None:
                    mrp = float(ps.get("price"))
            except (TypeError, ValueError):
                pass
        if mrp is None and sell is not None:
            mrp = sell

    # Pack size from name or sku field
    pack, unit = parse_pack(name)
    if pack is None and item.get("sku"):
        pack, unit = parse_pack(str(item.get("sku")))

    product = RawProduct(
        name=name.strip(),
        brand=brand_name.strip() if isinstance(brand_name, str) and brand_name.strip() else None,
        subcategory=detect_subcategory(name) or detect_subcategory(desc or ""),
        category=detect_category(name),
        description=desc,
        source_url=url,
    )
    sku = RawSku(
        product=name.strip(),
        brand=product.brand,
        variant="Regular",
        pack_size=pack,
        unit=unit,
        mrp=mrp,
        selling_price=sell,
        flavour=item.get("color") if isinstance(item.get("color"), str) else None,
        source_url=url,
    )
    return product, sku


def _extract_brands(soup: BeautifulSoup, url: str) -> list[RawBrand]:
    brands: list[RawBrand] = []
    seen: set[str] = set()
    # Heuristic: links/text under anchors with "brand" nearby, or repeated brand cards.
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ").split())
        if not text or len(text) > 60:
            continue
        # Brand-like: short title that isn't a nav boilerplate
        low = text.lower()
        if low in ("home", "about", "contact", "products", "brands", "careers", "more", "read more", "view all"):
            continue
        # Only take as brand if parent section mentions brand OR path has /brand
        href = a.get("href", "")
        if "/brand" in href.lower() or "brands" in url.lower():
            if text not in seen and len(text.split()) <= 4:
                seen.add(text)
                brands.append(RawBrand(name=text, source_url=url))
    return brands[:30]


def _extract_products_from_listing(soup: BeautifulSoup, url: str) -> list[tuple[RawProduct, RawSku]]:
    """Fallback: find product cards via common patterns (no JSON-LD)."""
    out: list[tuple[RawProduct, RawSku]] = []
    seen: set[str] = set()

    # Pattern 1: elements with class containing product/card/item
    for el in soup.find_all(True, class_=re.compile(r"(product|card|item|sku)", re.I)):
        # Get title: h1-h4, strong, or class*=title|name
        title_el = None
        for sel in el.find_all(["h1", "h2", "h3", "h4", "strong"]):
            title_el = sel
            break
        if title_el is None:
            title_el = el.find(class_=re.compile(r"(title|name|heading)", re.I))
        if not title_el:
            continue
        name = " ".join(title_el.get_text(" ").split())
        if not name or len(name) < 3 or len(name) > 120:
            continue
        if name.lower() in seen:
            continue
        # Price text
        price_el = el.find(class_=re.compile(r"(price|mrp|cost)", re.I))
        price_text = price_el.get_text(" ") if price_el else el.get_text(" ")
        mrp, sell = parse_price(price_text)
        pack, unit = parse_pack(name + " " + price_text)
        link = el.find("a", href=True)
        purl = abs_url(url, link["href"]) if link else url
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        brand_name = None
        # brand from data attr or parent heading
        brand_el = el.find(class_=re.compile(r"brand", re.I))
        if brand_el:
            brand_name = " ".join(brand_el.get_text(" ").split())[:80] or None
        product = RawProduct(
            name=name,
            brand=brand_name,
            subcategory=detect_subcategory(name),
            category=detect_category(name),
            source_url=purl or url,
        )
        sku = RawSku(
            product=name,
            brand=brand_name,
            variant="Regular",
            pack_size=pack,
            unit=unit,
            mrp=mrp,
            selling_price=sell,
            source_url=purl or url,
        )
        out.append((product, sku))
        if len(out) >= 40:
            break
    return out


def _extract_distributors(soup: BeautifulSoup, url: str) -> list[RawDistributor]:
    out: list[RawDistributor] = []
    seen: set[str] = set()
    for el in soup.find_all(True, class_=re.compile(r"(distributor|dealer|partner|stockist|channel)", re.I)):
        # Try to find a name
        name_el = el.find(["h2", "h3", "h4", "strong", "b"]) or el
        name = " ".join(name_el.get_text(" ").split())
        # Sometimes the card has lots of text — take first line-like chunk
        if len(name) > 120:
            name = name[:120]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        text = el.get_text(" ").lower()
        dtype = None
        if "national" in text:
            dtype = "national"
        elif "regional" in text:
            dtype = "regional"
        elif "local" in text:
            dtype = "local"
        # state detection (from known list tokens)
        state = None
        for st in ("Gujarat", "Maharashtra", "Karnataka", "Tamil Nadu", "Andhra Pradesh",
                   "Telangana", "Kerala", "Punjab", "Haryana", "Delhi", "Rajasthan",
                   "Uttar Pradesh", "Madhya Pradesh", "West Bengal", "Bihar", "Odisha", "Goa"):
            if st.lower() in text:
                state = st
                break
        out.append(RawDistributor(name=name, type=dtype, state=state, source_url=url))
        if len(out) >= 40:
            break
    return out


def extract_about(cfg: CompanyCfg, url: str, html: str, payload: RawPayload) -> None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        payload.description = " ".join(meta["content"].split())[:4000]
        payload.source_url = payload.source_url or url
    if not payload.description:
        # First big paragraph blocks
        paras = []
        for p in soup.find_all("p"):
            t = " ".join(p.get_text(" ").split())
            if len(t) > 80:
                paras.append(t)
            if sum(len(x) for x in paras) > 1500:
                break
        if paras:
            payload.description = " ".join(paras)[:4000]


def extract_website(client: HttpClient, cfg: CompanyCfg) -> RawPayload:
    """Crawl a company website (bounded) and build a RawPayload."""
    payload = RawPayload(
        company_slug=cfg.slug,
        source_type="website",
        source_url=cfg.base_url,
        confidence="medium",
    )

    # 1. Sitemap discovery
    try:
        sitemap_urls = discover_sitemap_urls(client, cfg.base_url)
        sitemap_urls = same_host_urls(sitemap_urls, cfg.base_url)
    except FetchError:
        sitemap_urls = []

    # Always include configured paths
    start_urls: list[str] = []
    for p in [cfg.about_path, *cfg.product_paths, *cfg.distributor_paths, *cfg.ir_paths]:
        if p.startswith("http"):
            start_urls.append(p)
        else:
            start_urls.append(f"{cfg.base_url}{p}")

    product_urls = filter_urls(sitemap_urls, include=list(PRODUCT_TOKENS),
                               exclude=list(SKIP_TOKENS), limit=25)
    # If sitemap is unhelpful, still try configured product paths
    if len(product_urls) < 3:
        product_urls = start_urls[1:4] + product_urls
    about_urls = filter_urls(sitemap_urls, include=list(ABOUT_TOKENS), limit=3) or [start_urls[0]]
    dist_urls = filter_urls(sitemap_urls, include=list(DISTRIBUTOR_TOKENS), limit=5)
    if not dist_urls:
        dist_urls = [f"{cfg.base_url}{p}" for p in cfg.distributor_paths[:2]]

    # 2. About page
    for u in about_urls[:2]:
        try:
            html = client.get_text(u)
        except FetchError:
            continue
        extract_about(cfg, u, html, payload)
        if payload.description:
            break

    # 3. Product/brand pages
    product_pages = (product_urls + start_urls[1:4])
    # Dedup preserve order
    seen_p: set[str] = set()
    uniq_product_pages: list[str] = []
    for u in product_pages:
        if u not in seen_p:
            seen_p.add(u)
            uniq_product_pages.append(u)

    for u in uniq_product_pages[:12]:
        try:
            html = client.get_text(u)
        except FetchError:
            continue
        soup = BeautifulSoup(html, "html.parser")
        # Brands from brand pages
        if any(t in u.lower() for t in BRAND_TOKENS) or "brand" in u.lower():
            for b in _extract_brands(soup, u):
                if not any(existing.name.lower() == b.name.lower() for existing in payload.brands):
                    payload.brands.append(b)
        # JSON-LD products (best)
        jl_products = _extract_jsonld_products(soup)
        if jl_products:
            for item in jl_products:
                prod, sku = _product_from_jsonld(item, u)
                if prod:
                    if not any(x.name.lower() == prod.name.lower() for x in payload.products):
                        payload.products.append(prod)
                    if sku:
                        payload.skus.append(sku)
        else:
            # CSS fallback
            for prod, sku in _extract_products_from_listing(soup, u):
                if not any(x.name.lower() == prod.name.lower() for x in payload.products):
                    payload.products.append(prod)
                # Only keep SKU if it has a price or pack
                if sku.mrp is not None or sku.selling_price is not None or sku.pack_size is not None:
                    payload.skus.append(sku)
        # If overrides specify brand/product selectors
        if cfg.overrides.get("brand_items"):
            for el in soup.select(cfg.overrides["brand_items"]):
                name = " ".join(el.get_text(" ").split())[:80]
                if name and not any(x.name.lower() == name.lower() for x in payload.brands):
                    payload.brands.append(RawBrand(name=name, source_url=u))
        if len(payload.products) >= 60:
            break

    # 4. Distributor pages
    for u in dist_urls[:3]:
        try:
            html = client.get_text(u)
        except FetchError:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for d in _extract_distributors(soup, u):
            if not any(x.name.lower() == d.name.lower() for x in payload.distributors):
                payload.distributors.append(d)
        # Also honor override selector
        if cfg.overrides.get("distributor_items"):
            for el in soup.select(cfg.overrides["distributor_items"]):
                name = " ".join(el.get_text(" ").split())[:120]
                if name and not any(x.name.lower() == name.lower() for x in payload.distributors):
                    payload.distributors.append(RawDistributor(name=name, source_url=u))

    # 5. Confidence + notes
    if payload.products or payload.skus:
        payload.confidence = "high"
    elif payload.brands:
        payload.confidence = "medium"
    else:
        payload.confidence = "low"
        payload.notes.append("No products/SKUs discovered on website; may need overrides.")

    if payload.brands and not payload.products:
        # Seed a placeholder product list? No — leave brands only.
        pass

    # If description missing but we have pages, keep source_url
    if not payload.description:
        payload.notes.append("No meta/paragraph description found on about pages.")

    return payload
