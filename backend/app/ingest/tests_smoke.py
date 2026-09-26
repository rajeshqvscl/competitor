"""Smoke tests for ingest (no DB required). Run: python -m app.ingest.tests_smoke"""
from __future__ import annotations

import sys

from app.ingest.normalize import (
    RawBrand, RawPayload, detect_category, detect_subcategory, fuzzy_in,
    parse_pack, parse_price, slugify,
)
from app.ingest.extract.report.pdf_text import PdfDoc
from app.ingest.extract.report.rules import extract_report_payload
from app.ingest.fetch.pages import filter_urls, find_pdf_links, same_host_urls
from app.ingest.extract.website.generic import (
    _extract_jsonld_products, _extract_products_from_listing, _product_from_jsonld,
)
from bs4 import BeautifulSoup

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  OK  {name}")
    else:
        failures.append(f"{name}: {detail}")
        print(f" FAIL {name} — {detail}")


def test_normalize() -> None:
    check("slugify", slugify("Amul Gold (Full Cream)") == "amul-gold-full-cream",
          slugify("Amul Gold (Full Cream)"))
    check("detect_category cheese", detect_category("Amul Cheese Slices") == "Cheese")
    check("detect_subcategory full cream", detect_subcategory("Amul Gold Full Cream Milk") == "Full Cream Milk")
    check("detect_subcategory curd", detect_subcategory("Heritage Curd Cup") == "Curd")
    pack, unit = parse_pack("Amul Gold 500ml pouch")
    check("parse_pack ml", pack == 500.0 and unit == "ml", f"{pack} {unit}")
    mrp, sell = parse_price("MRP: Rs. 40, price Rs. 36")
    check("parse_price mrp+sell", mrp == 40 and sell == 36, f"mrp={mrp} sell={sell}")
    mrp2, sell2 = parse_price("₹68 only")
    check("parse_price single", mrp2 == 68 and sell2 == 68, f"mrp={mrp2} sell={sell2}")
    check("fuzzy exact", fuzzy_in("amul gold", ["Amul Gold"]) == "Amul Gold")
    check("fuzzy partial", fuzzy_in("Amul Gold Milk", ["Amul Gold"]) == "Amul Gold")
    p = RawPayload(company_slug="x", source_type="website", source_url="http://x")
    check("empty payload", p.is_empty())
    p.brands.append(RawBrand(name="A"))
    check("non-empty payload", not p.is_empty())


def test_report_rules() -> None:
    text = """ANNUAL REPORT 2025
Acme Dairy Ltd
COMPANY OVERVIEW
Acme Dairy is a leading cooperative dairy processor headquartered in Gujarat.
It operates 12 plants across western and southern India.

BRAND PORTFOLIO
Acme Gold
Acme Taaza
Acme Fresh
Acme Delight

MARKET PRESENCE
The company has strong presence in Gujarat, Maharashtra, Karnataka and Tamil Nadu.
Plants are located at Ahmedabad, Pune and Bengaluru.

SEGMENT REPORTING
Revenue from operations | Crore
Dairy | 5200
Snacks | 800
"""
    doc = PdfDoc(path="mem", text=text, pages=[text],
                 tables=[[["Revenue from operations", "Amount"], ["Dairy", "5200"]]])
    payload = extract_report_payload("acme", "http://example.com/ar.pdf", doc, "Acme Dairy Ltd")
    brands = [b.name for b in payload.brands]
    check("ar description", bool(payload.description), payload.description or "none")
    check("ar brands", "Acme Gold" in brands and "MARKET PRESENCE" not in brands, str(brands))
    check("ar regions", "Gujarat" in payload.regions and "Maharashtra" in payload.regions,
          str(payload.regions))
    check("ar facts", len(payload.facts) >= 1, str(payload.facts))
    check("ar confidence high", payload.confidence == "high", payload.confidence)


def test_website_extract() -> None:
    html = """<html><head>
<script type="application/ld+json">
{"@type":"Product","name":"Amul Gold Full Cream Milk 500ml","brand":{"name":"Amul Gold"},
"offers":{"price":"36","priceCurrency":"INR","priceSpecification":{"price":"38"}}}
</script></head>
<body><div class="product-card"><h3>Amul Taaza Toned Milk 1L</h3><span class="price">Rs. 68</span></div></body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    jl = _extract_jsonld_products(soup)
    check("jsonld found", len(jl) == 1, str(len(jl)))
    prod, sku = _product_from_jsonld(jl[0], "http://x/p")
    check("jsonld name", prod and "Amul Gold" in prod.name, prod.name if prod else "none")
    check("jsonld price", sku and sku.selling_price == 36 and sku.mrp == 38,
          f"mrp={sku.mrp} sell={sku.selling_price}" if sku else "none")
    cards = _extract_products_from_listing(soup, "http://x/list")
    names = [p.name for p, _ in cards]
    check("css card product", any("Taaza" in n for n in names), str(names))


def test_pages() -> None:
    html = ('<a href="/pdf/annual-report-2025.pdf">AR</a> '
            '<a href="https://other.com/x.pdf">x</a> '
            '<a href="/brochure.pdf">b</a>')
    links = find_pdf_links(html, "http://example.com", keywords=("annual", "report"))
    check("pdf keyword filter", len(links) == 1 and "annual-report-2025.pdf" in links[0], str(links))
    urls = ["http://a.com/products/milk", "http://a.com/about", "http://b.com/x",
            "http://a.com/careers/jobs"]
    same = same_host_urls(urls, "http://a.com")
    check("same host", len(same) == 3, str(same))
    filtered = filter_urls(same, include=["product"], exclude=["career"])
    check("filter urls", filtered == ["http://a.com/products/milk"], str(filtered))


def test_config() -> None:
    from app.ingest.config import COMPANIES, get_company, all_slugs
    check("15 companies", len(COMPANIES) == 15, str(len(COMPANIES)))
    check("unique slugs", len(set(all_slugs())) == 15)
    check("get_company", get_company("amul") is not None)
    check("get_company unknown", get_company("nope") is None)


def main() -> int:
    print("== ingest smoke tests ==")
    test_normalize()
    test_report_rules()
    test_website_extract()
    test_pages()
    test_config()
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nAll passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
