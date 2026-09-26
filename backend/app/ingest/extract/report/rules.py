"""Rule-based section extraction from annual-report PDF text."""
from __future__ import annotations

import re
from typing import Optional

from app.ingest.extract.report.pdf_text import PdfDoc
from app.ingest.normalize import (
    RawBrand, RawPayload, detect_category, detect_subcategory,
)

# Section heading patterns (case-insensitive)
BRAND_HEADINGS = re.compile(
    r"(?im)^\s*(brand\s*portfolio|our\s*brands|product\s*brands|brands?\s*overview|brand\s*architecture)\s*$"
)
GEO_HEADINGS = re.compile(
    r"(?im)^\s*(geograph\w*|market\s*presence|regional\s*presence|footprint|locations?|plants?\s*(?:&|and)\s*markets?|distribution\s*network)\s*$"
)
SUBSIDIARY_HEADINGS = re.compile(
    r"(?im)^\s*(subsidiar\w*|associat\w*|joint\s*ventur\w*|group\s*companies|group\s*entities)\s*$"
)
SEGMENT_HEADINGS = re.compile(
    r"(?im)^\s*(segment\s*(?:wise|reporting|information)?|revenue\s*(?:from\s*)?(?:operations|by\s*segment)|business\s*segment)\s*$"
)
OVERVIEW_HEADINGS = re.compile(
    r"(?im)^\s*(company\s*overview|about\s*(?:us|the\s*company)|business\s*overview|our\s*business)\s*$"
)

# Known Indian states for geo extraction (matches seed regions.csv states)
STATES = [
    "Delhi NCR", "Delhi", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan",
    "Maharashtra", "Gujarat", "Madhya Pradesh", "Goa", "Karnataka", "Tamil Nadu",
    "Andhra Pradesh", "Telangana", "Kerala", "West Bengal", "Bihar", "Odisha",
    "Assam", "Chhattisgarh", "Jharkhand", "Uttarakhand", "Himachal Pradesh",
    "Jammu and Kashmir", "Puducherry", "Chandigarh",
]
_STATE_SET = {s.lower(): s for s in STATES}

# Common non-brand words to filter out of brand lists
_STOP = {
    "the", "and", "our", "we", "ltd", "limited", "pvt", "private", "india",
    "annual", "report", "company", "group", "milk", "dairy", "products",
    "home", "about", "more", "read", "view", "click", "page", "note",
}


def _clean_line(line: str) -> str:
    return re.sub(r"[^A-Za-z0-9 &'()+./-]", "", line).strip()


def _section(text: str, heading_re: re.Pattern, next_headings: list[re.Pattern],
             max_chars: int = 6000) -> Optional[str]:
    """Grab text after a heading until next known heading or max_chars."""
    m = heading_re.search(text)
    if not m:
        return None
    start = m.end()
    end = min(len(text), start + max_chars)
    # Stop early at next heading-like line (always — sections can be short)
    rest = text[start:end]
    for nh in next_headings:
        m2 = nh.search(rest)
        if m2 and m2.start() > 10:
            rest = rest[: m2.start()]
            break
    return rest.strip()


def extract_brands_from_section(section: str) -> list[str]:
    """Pull brand-like names from a brand portfolio section (lines or bullet lists)."""
    names: list[str] = []
    seen: set[str] = set()
    for raw_line in section.splitlines():
        line = _clean_line(raw_line)
        if not line or len(line) < 2 or len(line) > 60:
            continue
        # Skip sentences (too many lowercase words + verbs)
        if line.count(" ") > 6:
            continue
        # Skip ALL-CAPS section headings
        if line.isupper() and len(line.split()) <= 5:
            continue
        # Bullet/list style or Title Case short labels
        words = line.split()
        if len(words) > 5:
            continue
        # Require at least one capitalised word (brand-like)
        if not any(w[:1].isupper() for w in words if w):
            continue
        low = line.lower().strip(".")
        if low in _STOP:
            continue
        if re.search(r"\d{4}", line):  # years
            continue
        if low not in seen:
            seen.add(low)
            names.append(line)
        if len(names) >= 40:
            break
    return names


def extract_regions_from_text(text: str) -> list[str]:
    found: list[str] = []
    low = text.lower()
    for key, canon in _STATE_SET.items():
        if key in low and canon not in found:
            found.append(canon)
    return found


def extract_description_from_overview(section: Optional[str], doc: PdfDoc) -> Optional[str]:
    if section:
        # First 1-2 paragraphs
        paras = [p.strip() for p in section.split("\n\n") if len(p.strip()) > 100]
        if paras:
            return " ".join(paras[:2])[:3000]
    # Fallback: first long paragraphs of doc mentioning the company once
    for page in doc.pages[:10]:
        for para in page.split("\n\n"):
            p = " ".join(para.split())
            if len(p) > 150 and re.search(r"\b(company|business|leading|manufacturer|dairy)\b", p, re.I):
                return p[:3000]
    return None


def extract_tables_facts(doc: PdfDoc, max_facts: int = 15) -> list[str]:
    """Capture short table summaries as evidence facts (segment revenue etc.)."""
    facts: list[str] = []
    for tbl in doc.tables[:40]:
        if not tbl or len(tbl) < 2:
            continue
        # Look for tables with revenue/amount indicators
        flat = " ".join(str(c or "") for row in tbl[:3] for c in row).lower()
        if not re.search(r"(revenue|turnover|sales|amount|₹|cr\b|crore|lakh)", flat):
            continue
        head = [str(c or "").strip() for c in tbl[0][:6]]
        row1 = [str(c or "").strip() for c in tbl[1][:6]]
        if any(head) and any(row1):
            facts.append("Table: " + " | ".join(head) + " // " + " | ".join(row1))
        if len(facts) >= max_facts:
            break
    return facts


def extract_report_payload(company_slug: str, source_url: str, doc: PdfDoc,
                           company_name: str) -> RawPayload:
    """Build a RawPayload from an annual-report PDF using rules."""
    text = doc.text
    payload = RawPayload(
        company_slug=company_slug,
        source_type="annual_report",
        source_url=source_url,
        confidence="medium",
    )

    # Description from overview section
    overview = _section(text, OVERVIEW_HEADINGS,
                         [BRAND_HEADINGS, GEO_HEADINGS, SEGMENT_HEADINGS, SUBSIDIARY_HEADINGS],
                         max_chars=5000)
    desc = extract_description_from_overview(overview, doc)
    if desc:
        payload.description = desc

    # Brands
    brand_sec = _section(text, BRAND_HEADINGS,
                         [GEO_HEADINGS, SEGMENT_HEADINGS, SUBSIDIARY_HEADINGS, OVERVIEW_HEADINGS],
                         max_chars=8000)
    if brand_sec:
        for name in extract_brands_from_section(brand_sec):
            # Skip if it's just the company name repeated
            if norm := name.lower():
                if company_name.split()[0].lower() in norm and len(name.split()) <= 2:
                    # still allow e.g. "Amul Gold" — only skip exact-ish company tokens
                    if norm in (company_name.lower(), company_name.split("(")[0].strip().lower()):
                        continue
            payload.brands.append(RawBrand(name=name, source_url=source_url))
        if payload.brands:
            payload.confidence = "high"

    # Regions / geography
    geo_sec = _section(text, GEO_HEADINGS,
                       [SEGMENT_HEADINGS, SUBSIDIARY_HEADINGS, BRAND_HEADINGS], max_chars=6000)
    geo_text = geo_sec or text[:30000]
    regions = extract_regions_from_text(geo_text)
    # Also scan plants section if present
    plant_sec = _section(text, re.compile(r"(?im)^\s*(?:plants?|manufacturing\s*(?:units?|facilities))\s*$"),
                         [], max_chars=4000)
    if plant_sec:
        for r in extract_regions_from_text(plant_sec):
            if r not in regions:
                regions.append(r)
    payload.regions = regions

    # Evidence facts from segment/financial tables
    payload.facts.extend(extract_tables_facts(doc))

    # Subsidiaries as notes (potential parent/related info)
    subs_sec = _section(text, SUBSIDIARY_HEADINGS, [SEGMENT_HEADINGS], max_chars=3000)
    if subs_sec:
        payload.notes.append("subsidiaries_section: " + " ".join(subs_sec.split())[:500])

    # If rules found little, lower confidence so loader/review treats carefully
    if not payload.brands and not payload.regions and not payload.description:
        payload.confidence = "low"
        payload.notes.append("Rule extraction found little; LLM fallback recommended.")

    return payload
