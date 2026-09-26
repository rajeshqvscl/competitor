"""Page discovery: sitemap.xml parsing + bounded same-host crawl helpers."""
import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from app.ingest.fetch.http import HttpClient, FetchError

SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}


def _parse_sitemap_xml(content: bytes) -> tuple[list[str], list[str]]:
    """Return (page_urls, child_sitemap_urls) from a sitemap or sitemapindex."""
    pages: list[str] = []
    children: list[str] = []
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return pages, children
    tag = root.tag.lower()
    if tag.endswith("sitemapindex"):
        for loc in root.findall("sm:sitemap/sm:loc", SITEMAP_NS):
            if loc.text:
                children.append(loc.text.strip())
        # Some servers omit namespaces.
        if not children:
            for loc in root.iter():
                if loc.tag.lower().endswith("loc") and loc.text:
                    children.append(loc.text.strip())
    else:
        for url_el in root.findall("sm:url/sm:loc", SITEMAP_NS):
            if url_el.text:
                pages.append(url_el.text.strip())
        if not pages:
            for loc in root.iter():
                if loc.tag.lower().endswith("loc") and loc.text:
                    pages.append(loc.text.strip())
    return pages, children


def discover_sitemap_urls(client: HttpClient, base_url: str, max_sitemaps: int = 5) -> list[str]:
    """Fetch robots-declared sitemaps + common sitemap paths; return page URLs."""
    base = base_url.rstrip("/")
    candidates = [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml", f"{base}/wp-sitemap.xml"]
    # robots.txt Sitemap: directives
    try:
        robots = client.get_text(f"{base}/robots.txt")
        for line in robots.splitlines():
            if line.lower().startswith("sitemap:"):
                sm = line.split(":", 1)[1].strip()
                if sm:
                    candidates.insert(0, sm)
    except FetchError:
        pass

    seen_sm: set[str] = set()
    pages: list[str] = []
    queue = list(candidates)
    while queue and len(seen_sm) < max_sitemaps:
        sm_url = queue.pop(0)
        if sm_url in seen_sm:
            continue
        seen_sm.add(sm_url)
        try:
            content = client.get_bytes(sm_url)
        except FetchError:
            continue
        child_pages, children = _parse_sitemap_xml(content)
        pages.extend(child_pages)
        queue.extend(children)
    return pages


def same_host_urls(urls: list[str], base_url: str) -> list[str]:
    host = urlparse(base_url).netloc
    out = []
    for u in urls:
        p = urlparse(u)
        if p.netloc == host and p.scheme in ("http", "https"):
            out.append(u)
    return out


def filter_urls(urls: list[str], include: list[str] | None = None, exclude: list[str] | None = None,
                limit: int = 60) -> list[str]:
    """Keep URLs matching any include substring; drop those matching exclude."""
    out: list[str] = []
    for u in urls:
        path = urlparse(u).path.lower()
        if include and not any(tok.lower() in path for tok in include):
            continue
        if exclude and any(tok.lower() in path for tok in exclude):
            continue
        if u not in out:
            out.append(u)
        if len(out) >= limit:
            break
    return out


def abs_url(base: str, href: str) -> str | None:
    if not href:
        return None
    u = urljoin(base, href.strip())
    if not u.startswith(("http://", "https://")):
        return None
    return u


PDF_LINK_RE = re.compile(r'href\s*=\s*["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', re.I)


def find_pdf_links(html: str, base_url: str, keywords: tuple[str, ...] = ()) -> list[str]:
    """Extract absolute PDF hrefs from HTML, optionally filtered by keywords in URL/text context."""
    found: list[str] = []
    for m in PDF_LINK_RE.finditer(html):
        href = m.group(1)
        url = abs_url(base_url, href)
        if not url:
            continue
        if keywords:
            low = url.lower()
            if not any(k.lower() in low for k in keywords):
                continue
        if url not in found:
            found.append(url)
    return found
