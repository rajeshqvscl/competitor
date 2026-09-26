"""Generic website scanner: crawl any URL and build an intelligence report.

Extracts: company meta (description, emails, phones, socials, address),
brands, products (JSON-LD first, CSS cards fallback), prices/pack sizes,
distributors/partners, and PDF links (annual reports / catalogs).

No DB writes here — pure extraction. /api/scan wraps it as a job.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.ingest.fetch.http import HttpClient, FetchError
from app.ingest.fetch.pages import (
    abs_url, discover_sitemap_urls, same_host_urls, filter_urls,
)
from app.ingest.normalize import parse_pack, parse_price, detect_subcategory

# ------------------------------------------------------------------ tuning

MAX_PAGES = 25          # hard cap on crawled pages
MAX_PRODUCTS = 60
MAX_BRANDS = 30
MAX_DISTRIBUTORS = 40
TIMEOUT_S = 45

SKIP_TOKENS = ("career", "job", "press", "media", "blog", "news", "privacy",
               "terms", "policy", "login", "cart", "checkout", "video",
               "gallery", "faq", "feedback", "webmail", "admin")

PRODUCT_TOKENS = ("product", "catalog", "range", "collection", "shop", "store",
                  "brand", "milk", "dairy", "cheese", "ghee", "curd", "paneer",
                  "ice-cream", "yogurt", "butter", "powder", "sweet", "lassi")

ABOUT_TOKENS = ("about", "who-we-are", "company", "profile", "overview", "story")
CONTACT_TOKENS = ("contact", "reach-us", "get-in-touch")
DISTRIBUTOR_TOKENS = ("distributor", "dealer", "partner", "channel", "stockist")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b")
SOCIAL_RE = re.compile(
    r"https?://(?:www\.)?(linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|youtube\.com)/[\w\-/.]+"
)
PDF_RE = re.compile(r'href\s*=\s*["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', re.I)

STATE_TOKENS = (
    "Gujarat", "Maharashtra", "Karnataka", "Tamil Nadu", "Andhra Pradesh",
    "Telangana", "Kerala", "Punjab", "Haryana", "Delhi", "Rajasthan",
    "Uttar Pradesh", "Madhya Pradesh", "West Bengal", "Bihar", "Odisha", "Goa",
    "Sikkim", "Assam", "Jharkhand", "Chhattisgarh", "Uttarakhand",
)


def _visible_text(soup: BeautifulSoup, limit: int = 5000) -> str:
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "svg"]):
        t.decompose()
    return " ".join(soup.get_text(separator=" ").split())[:limit]


# ------------------------------------------------------------------ extractors

def extract_company_meta(soup: BeautifulSoup, url: str, html: str) -> dict:
    meta: dict = {"name": None, "description": None, "logo_url": None}

    # Name: og:site_name > title
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content"):
        meta["name"] = og["content"].strip()
    if not meta["name"] and soup.title and soup.title.string:
        meta["name"] = " ".join(soup.title.string.split())[:120]

    # Description: meta description > og:description > first big paragraphs
    for sel in (
        {"name": "description"},
        {"property": "og:description"},
    ):
        m = soup.find("meta", attrs=sel)
        if m and m.get("content") and m["content"].strip():
            meta["description"] = " ".join(m["content"].split())[:4000]
            break
    if not meta["description"]:
        paras = []
        for p in soup.find_all("p"):
            t = " ".join(p.get_text(" ").split())
            if len(t) > 80:
                paras.append(t)
            if sum(len(x) for x in paras) > 1500:
                break
        if paras:
            meta["description"] = " ".join(paras)[:4000]

    # Logo: og:image or first svg/img with 'logo' in attrs
    og_img = soup.find("meta", attrs={"property": "og:image"})
    if og_img and og_img.get("content"):
        meta["logo_url"] = abs_url(url, og_img["content"])
    if not meta["logo_url"]:
        img = soup.find("img", src=re.compile(r"logo", re.I)) or \
              soup.find("img", class_=re.compile(r"logo", re.I))
        if img:
            meta["logo_url"] = abs_url(url, img.get("src", ""))

    # Emails / phones / socials / PDFs from raw HTML
    # Exclude static-asset matches like 'Asset-1@2x-50x100.png' from srcset attrs
    asset_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".css", ".js")
    emails = {e for e in EMAIL_RE.findall(html) if not e.lower().endswith(asset_exts)}
    meta["emails"] = sorted(emails)[:10]
    phones = [p.replace("-", " ") for p in PHONE_RE.findall(html)]
    meta["phones"] = sorted(set(phones))[:10]
    meta["socials"] = sorted(set(m.group(0) for m in SOCIAL_RE.finditer(html)))[:8]

    # States mentioned (presence signal)
    text = _visible_text(soup, 12000).lower()
    meta["states_mentioned"] = [s for s in STATE_TOKENS if s.lower() in text][:10]
    return meta


def extract_jsonld_products(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """Return normalized product dicts from JSON-LD on this page."""
    out: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        stack = list(items)
        while stack:
            item = stack.pop(0)
            if isinstance(item, list):
                stack.extend(item)
                continue
            if not isinstance(item, dict):
                continue
            g = item.pop("@graph", None)
            if isinstance(g, list):
                stack.extend(g)
            t = item.get("@type")
            types = [t] if not isinstance(t, list) else t
            if not any(str(x).lower() == "product" for x in types):
                continue
            name = item.get("name")
            if not name or not isinstance(name, str):
                continue
            brand = item.get("brand")
            if isinstance(brand, dict):
                brand = brand.get("name")
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            mrp = sell = None
            if isinstance(offers, dict):
                price = offers.get("price") or offers.get("lowPrice")
                try:
                    sell = float(price) if price is not None else None
                except (TypeError, ValueError):
                    sell = None
                ps = offers.get("priceSpecification")
                if isinstance(ps, dict) and ps.get("price"):
                    try:
                        mrp = float(ps["price"])
                    except (TypeError, ValueError):
                        pass
                if mrp is None and sell is not None:
                    mrp = sell
            pack, unit = parse_pack(name)
            if pack is None and item.get("sku"):
                pack, unit = parse_pack(str(item["sku"]))
            desc = item.get("description")
            out.append({
                "name": name.strip()[:150],
                "brand": brand.strip()[:80] if isinstance(brand, str) and brand else None,
                "description": " ".join(desc.split())[:500] if isinstance(desc, str) else None,
                "subcategory": detect_subcategory(name),
                "pack_size": pack,
                "unit": unit,
                "mrp": mrp,
                "selling_price": sell,
                "source_url": page_url,
            })
            if len(out) >= MAX_PRODUCTS:
                return out
    return out


def extract_products_css(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """Fallback: product cards via common CSS patterns."""
    out: list[dict] = []
    seen: set[str] = set()
    for el in soup.find_all(True, class_=re.compile(r"(product|card|item|sku)", re.I)):
        title_el = el.find(["h1", "h2", "h3", "h4", "strong"]) or \
                   el.find(class_=re.compile(r"(title|name|heading)", re.I))
        if not title_el:
            continue
        name = " ".join(title_el.get_text(" ").split())
        if not name or len(name) < 3 or len(name) > 120 or name.lower() in seen:
            continue
        price_el = el.find(class_=re.compile(r"(price|mrp|cost)", re.I))
        price_text = price_el.get_text(" ") if price_el else el.get_text(" ")
        mrp, sell = parse_price(price_text)
        pack, unit = parse_pack(name + " " + price_text)
        link = el.find("a", href=True)
        purl = abs_url(page_url, link["href"]) if link else page_url
        brand_el = el.find(class_=re.compile(r"brand", re.I))
        brand = " ".join(brand_el.get_text(" ").split())[:80] or None if brand_el else None
        seen.add(name.lower())
        out.append({
            "name": name,
            "brand": brand,
            "description": None,
            "subcategory": detect_subcategory(name),
            "pack_size": pack,
            "unit": unit,
            "mrp": mrp,
            "selling_price": sell,
            "source_url": purl or page_url,
        })
        if len(out) >= MAX_PRODUCTS:
            break
    return out


def extract_brands_heuristic(soup: BeautifulSoup, page_url: str) -> list[str]:
    brands: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ").split())
        low = text.lower()
        if not text or len(text) > 60 or low in (
            "home", "about", "contact", "products", "brands", "careers",
            "more", "read more", "view all",
        ):
            continue
        href = a.get("href", "")
        if "/brand" in href.lower() or "brands" in page_url.lower():
            if text not in seen and len(text.split()) <= 4:
                seen.add(text)
                brands.append(text)
    return brands[:MAX_BRANDS]


def extract_distributors(soup: BeautifulSoup, page_url: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for el in soup.find_all(True, class_=re.compile(r"(distributor|dealer|partner|stockist|channel)", re.I)):
        name_el = el.find(["h2", "h3", "h4", "strong", "b"]) or el
        name = " ".join(name_el.get_text(" ").split())[:120]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        text = el.get_text(" ").lower()
        dtype = "national" if "national" in text else \
                "regional" if "regional" in text else \
                "local" if "local" in text else None
        state = next((s for s in STATE_TOKENS if s.lower() in text), None)
        out.append({"name": name, "type": dtype, "state": state, "source_url": page_url})
        if len(out) >= MAX_DISTRIBUTORS:
            break
    return out


# ------------------------------------------------------------------ orchestrator

def scan_website(url: str, rate_ms: int = 800) -> dict:
    """Crawl a website (bounded) and return a structured report dict."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    host = parsed.netloc

    report: dict = {
        "scanned_url": url,
        "host": host,
        "pages_crawled": 0,
        "description": None,
        "company_name": None,
        "logo_url": None,
        "emails": [], "phones": [], "socials": [],
        "states_mentioned": [],
        "brands": [],
        "products": [],
        "distributors": [],
        "pdf_links": [],
        "pages": [],          # list of {url, title, kind}
        "errors": [],
        "notes": [],
    }

    client = HttpClient(rate_ms=rate_ms)

    # 1. Sitemap discovery
    try:
        sitemap_urls = discover_sitemap_urls(client, base_url)
        sitemap_urls = same_host_urls(sitemap_urls, base_url)
    except FetchError:
        sitemap_urls = []

    product_urls = filter_urls(sitemap_urls, include=list(PRODUCT_TOKENS),
                               exclude=list(SKIP_TOKENS), limit=15)
    about_urls = filter_urls(sitemap_urls, include=list(ABOUT_TOKENS), limit=3) or [base_url + "/"]
    contact_urls = filter_urls(sitemap_urls, include=list(CONTACT_TOKENS), limit=2)
    dist_urls = filter_urls(sitemap_urls, include=list(DISTRIBUTOR_TOKENS), limit=4)

    # Always try common fallback paths if sitemap is unhelpful
    if not product_urls:
        product_urls = [base_url + p for p in ("/products", "/product", "/brands", "/our-products")]
    if not dist_urls:
        dist_urls = [base_url + p for p in ("/distributors", "/dealer", "/partners", "/channel-partners")]

    # 2. Homepage first (meta + brand signals)
    all_meta: dict = {}
    try:
        html = client.get_text(base_url + "/")
        soup = BeautifulSoup(html, "html.parser")
        all_meta = extract_company_meta(soup, base_url + "/", html)
        report["pages"].append({"url": base_url + "/", "title": all_meta.get("company_name"), "kind": "home"})
        report["pages_crawled"] += 1
    except FetchError as e:
        report["errors"].append(f"homepage fetch failed: {e}")
        # If homepage itself fails, bail early
        report["notes"].append("Could not fetch homepage — site may block bots or be offline.")
        report["confidence"] = "low"
        return report

    report["company_name"] = all_meta.get("name")
    report["description"] = all_meta.get("description")
    report["logo_url"] = all_meta.get("logo_url")
    report["emails"] = all_meta.get("emails", [])
    report["phones"] = all_meta.get("phones", [])
    report["socials"] = all_meta.get("socials", [])
    report["states_mentioned"] = all_meta.get("states_mentioned", [])
    report["pdf_links"] = sorted(set(abs_url(base_url + "/", m.group(1))
                                     for m in PDF_RE.finditer(html)))[:15]

    # 3. About pages (may improve description)
    for u in about_urls[:2]:
        if report["pages_crawled"] >= MAX_PAGES:
            break
        try:
            html2 = client.get_text(u)
            soup2 = BeautifulSoup(html2, "html.parser")
            m2 = extract_company_meta(soup2, u, html2)
            report["pages"].append({"url": u, "title": m2.get("company_name"), "kind": "about"})
            report["pages_crawled"] += 1
            if m2.get("description") and (not report["description"] or len(m2["description"]) > len(report["description"])):
                report["description"] = m2["description"]
            for k in ("emails", "phones", "socials"):
                got = m2.get(k, [])
                report[k] = sorted(set(report[k]) | set(got))[:10]
            for st in m2.get("states_mentioned", []):
                if st not in report["states_mentioned"]:
                    report["states_mentioned"].append(st)
            for m in PDF_RE.finditer(html2):
                pdf = abs_url(u, m.group(1))
                if pdf and pdf not in report["pdf_links"]:
                    report["pdf_links"].append(pdf)
        except FetchError:
            continue

    # 4. Product pages
    brand_counter: Counter = Counter()
    for u in product_urls[:12]:
        if report["pages_crawled"] >= MAX_PAGES:
            break
        try:
            html3 = client.get_text(u)
            soup3 = BeautifulSoup(html3, "html.parser")
            report["pages"].append({"url": u, "title": None, "kind": "products"})
            report["pages_crawled"] += 1

            prods = extract_jsonld_products(soup3, u)
            if not prods:
                prods = extract_products_css(soup3, u)
            for p in prods:
                if not any(x["name"].lower() == p["name"].lower() for x in report["products"]):
                    report["products"].append(p)
                if p.get("brand"):
                    brand_counter[p["brand"]] += 1

            for b in extract_brands_heuristic(soup3, u):
                brand_counter[b] += 1

            if len(report["products"]) >= MAX_PRODUCTS:
                break
        except FetchError:
            continue

    report["brands"] = [b for b, _ in brand_counter.most_common(MAX_BRANDS)]

    # 5. Distributor pages
    for u in dist_urls[:3]:
        if report["pages_crawled"] >= MAX_PAGES:
            break
        try:
            html4 = client.get_text(u)
            soup4 = BeautifulSoup(html4, "html.parser")
            report["pages"].append({"url": u, "title": None, "kind": "distributors"})
            report["pages_crawled"] += 1
            for d in extract_distributors(soup4, u):
                if not any(x["name"].lower() == d["name"].lower() for x in report["distributors"]):
                    report["distributors"].append(d)
        except FetchError:
            continue

    # 6. Contact page (emails/phones)
    for u in contact_urls[:2]:
        if report["pages_crawled"] >= MAX_PAGES:
            break
        try:
            html5 = client.get_text(u)
            soup5 = BeautifulSoup(html5, "html.parser")
            report["pages"].append({"url": u, "title": None, "kind": "contact"})
            report["pages_crawled"] += 1
            m5 = extract_company_meta(soup5, u, html5)
            for k in ("emails", "phones", "socials"):
                got = m5.get(k, [])
                report[k] = sorted(set(report[k]) | set(got))[:10]
        except FetchError:
            continue

    # 7. Confidence + notes
    if report["products"]:
        report["confidence"] = "high"
    elif report["brands"] or report["description"]:
        report["confidence"] = "medium"
    else:
        report["confidence"] = "low"
        report["notes"].append("Very little extracted — site may be JS-rendered (SPA) or blocking bots.")

    if not report["description"]:
        report["notes"].append("No meta/paragraph description found.")
    if not report["products"]:
        report["notes"].append("No products found — try a direct product page URL.")

    return report
