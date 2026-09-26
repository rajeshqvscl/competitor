"""Annual report PDF discovery (IR pages / pinned URLs) and download."""
import hashlib
import os
import re

from app.ingest.config import CompanyCfg
from app.ingest.fetch.http import HttpClient, FetchError
from app.ingest.fetch.pages import abs_url, find_pdf_links, same_host_urls

REPORT_KEYWORDS = (
    "annual",
    "report",
    "ar-2",
    "annual-report",
    "annualreport",
    "financial-year",
    "integrated-report",
)

# Prefer recent FYs when sorting candidates.
_FY_RE = re.compile(r"(?:20)(\d{2})")


def _score_pdf(url: str) -> int:
    low = url.lower()
    score = 0
    if "annual" in low:
        score += 4
    if "report" in low:
        score += 3
    if "financial" in low:
        score += 1
    m = _FY_RE.findall(low)
    if m:
        year = int(m[-1])
        # 18..30 maps to 2018..2030 — prefer newest.
        score += max(0, min(year, 30))
    return score


def discover_report_urls(client: HttpClient, cfg: CompanyCfg, max_pages: int = 6) -> list[str]:
    """Discover latest annual-report PDF URLs for a company (pinned first, then IR pages)."""
    candidates: list[str] = list(cfg.report_urls)
    host = cfg.base_url
    for path in cfg.ir_paths:
        if len(candidates) >= 5:
            break
        url = path if path.startswith("http") else f"{host}{path}"
        try:
            html = client.get_text(url)
        except FetchError:
            continue
        pdfs = find_pdf_links(html, url, keywords=REPORT_KEYWORDS)
        pdfs = same_host_urls(pdfs, host) or pdfs
        candidates.extend(pdfs)

    # Dedup + score
    seen: set[str] = set()
    ranked: list[str] = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            ranked.append(u)
    ranked.sort(key=_score_pdf, reverse=True)
    return ranked[:max_pages]


def download_report(client: HttpClient, pdf_url: str, cache_dir: str) -> str:
    """Download PDF to cache_dir; return local path. Skips if already cached."""
    os.makedirs(cache_dir, exist_ok=True)
    name = hashlib.sha256(pdf_url.encode()).hexdigest()[:16]
    # Keep a readable suffix from the URL.
    tail = re.sub(r"[^A-Za-z0-9._-]", "_", pdf_url.split("/")[-1].split("?")[0])[:60]
    if not tail.lower().endswith(".pdf"):
        tail = f"{tail}.pdf"
    path = os.path.join(cache_dir, f"{name}_{tail}")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    data = client.get_bytes(pdf_url)
    if not data[:5].startswith(b"%PDF"):
        # Some servers wrap PDFs; still save if substantial, else reject.
        if len(data) < 1024:
            raise FetchError(f"Downloaded content is not a PDF: {pdf_url}")
    with open(path, "wb") as f:
        f.write(data)
    return path
