"""Pipeline orchestrator: fetch → extract → normalize → load for one/all companies."""
from __future__ import annotations

import os
from typing import Iterable, Optional

from app.db import SessionLocal
from app.ingest.config import COMPANIES, CompanyCfg, get_company
from app.ingest.fetch.http import HttpClient, FetchError
from app.ingest.fetch.pdf import discover_report_urls, download_report
from app.ingest.loader import Loader, LoadStats
from app.ingest.normalize import RawPayload
from app.ingest.extract.website.generic import extract_website
from app.ingest.extract.report.pdf_text import extract_pdf
from app.ingest.extract.report.rules import extract_report_payload
from app.ingest.extract.report.llm import extract_with_llm, llm_enabled, merge_payloads

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "cache", "reports"))


def _rate_ms() -> int:
    try:
        return int(os.environ.get("INGEST_RATE_MS", "1000"))
    except ValueError:
        return 1000


def extract_company_website(cfg: CompanyCfg, client: HttpClient) -> RawPayload:
    return extract_website(client, cfg)


def extract_company_reports(cfg: CompanyCfg, client: HttpClient,
                            max_reports: int = 1) -> list[RawPayload]:
    payloads: list[RawPayload] = []
    try:
        urls = discover_report_urls(client, cfg)
    except FetchError as e:
        return [RawPayload(company_slug=cfg.slug, source_type="annual_report",
                           source_url=cfg.base_url, confidence="low",
                           notes=[f"Report discovery failed: {e}"])]
    if not urls:
        return [RawPayload(company_slug=cfg.slug, source_type="annual_report",
                           source_url=cfg.base_url, confidence="low",
                           notes=["No annual report PDF found (check ir_paths/report_urls in config)."])]

    for pdf_url in urls[:max_reports]:
        try:
            local = download_report(client, pdf_url, CACHE_DIR)
        except FetchError as e:
            payloads.append(RawPayload(company_slug=cfg.slug, source_type="annual_report",
                                       source_url=pdf_url, confidence="low",
                                       notes=[f"Download failed: {e}"]))
            continue
        try:
            doc = extract_pdf(local)
        except Exception as e:
            payloads.append(RawPayload(company_slug=cfg.slug, source_type="annual_report",
                                       source_url=pdf_url, confidence="low",
                                       notes=[f"PDF parse failed: {e}"]))
            continue

        rule_payload = extract_report_payload(cfg.slug, pdf_url, doc, cfg.name)

        # Hybrid: LLM if rules weak or always as supplement when enabled
        need_llm = rule_payload.confidence != "high" or len(rule_payload.brands) < 3
        if llm_enabled() and need_llm:
            llm_payload = extract_with_llm(doc.text, cfg.name, pdf_url, cfg.slug)
            if llm_payload:
                rule_payload = merge_payloads(rule_payload, llm_payload)

        if rule_payload.confidence == "low" and not rule_payload.brands and not rule_payload.regions:
            # Send straight to review as ambiguous evidence
            rule_payload.notes.append("Low confidence extraction — review recommended.")
        payloads.append(rule_payload)
    return payloads


def run_company(cfg: CompanyCfg, sources: tuple[str, ...] = ("website", "report"),
                dry_run: bool = False) -> list[LoadStats]:
    """Extract + load one company. Returns list of LoadStats (one per payload)."""
    results: list[LoadStats] = []
    with HttpClient(rate_ms=_rate_ms()) as client:
        payloads: list[RawPayload] = []
        if "website" in sources:
            try:
                payloads.append(extract_company_website(cfg, client))
            except Exception as e:
                st = LoadStats(company=cfg.slug)
                st.errors.append(f"website extract failed: {e}")
                results.append(st)
        if "report" in sources or "reports" in sources:
            try:
                payloads.extend(extract_company_reports(cfg, client))
            except Exception as e:
                st = LoadStats(company=cfg.slug)
                st.errors.append(f"report extract failed: {e}")
                results.append(st)

        for payload in payloads:
            if payload.is_empty() and payload.confidence == "low" and not payload.notes:
                continue
            db = SessionLocal()
            try:
                loader = Loader(db, dry_run=dry_run)
                st = loader.load(payload)
                st.company = f"{cfg.slug}:{payload.source_type}"
                results.append(st)
            except Exception as e:
                db.rollback()
                st = LoadStats(company=f"{cfg.slug}:{payload.source_type}")
                st.errors.append(f"load failed: {e}")
                results.append(st)
            finally:
                db.close()
    return results


def run_all(slugs: Optional[Iterable[str]] = None,
            sources: tuple[str, ...] = ("website", "report"),
            dry_run: bool = False) -> list[LoadStats]:
    """Run pipeline for selected slugs (default: all). Isolates per-company errors."""
    if slugs is None:
        targets: list[str] = [c.slug for c in COMPANIES]
    else:
        targets = list(slugs)

    all_stats: list[LoadStats] = []
    for slug in targets:
        c = get_company(slug)
        if c is None:
            st = LoadStats(company=slug)
            st.errors.append(f"unknown company slug '{slug}'")
            all_stats.append(st)
            continue
        try:
            stats = run_company(c, sources=sources, dry_run=dry_run)
            all_stats.extend(stats)
        except Exception as e:
            st = LoadStats(company=c.slug)
            st.errors.append(f"run failed: {e}")
            all_stats.append(st)
    return all_stats


def summarize(stats: list[LoadStats]) -> dict:
    total = {
        "companies": len(stats),
        "brands_created": 0,
        "products_created": 0,
        "skus_created": 0,
        "skus_updated": 0,
        "regions_created": 0,
        "region_links": 0,
        "distributors_created": 0,
        "price_records": 0,
        "change_events": 0,
        "review_items": 0,
        "sources": 0,
        "errors": 0,
    }
    for s in stats:
        total["brands_created"] += s.brands_created
        total["products_created"] += s.products_created
        total["skus_created"] += s.skus_created
        total["skus_updated"] += s.skus_updated
        total["regions_created"] += s.regions_created
        total["region_links"] += s.region_links
        total["distributors_created"] += s.distributors_created
        total["price_records"] += s.price_records
        total["change_events"] += s.change_events
        total["review_items"] += s.review_items
        total["sources"] += s.sources
        total["errors"] += len(s.errors)
    return total
