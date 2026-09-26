"""Scraper control API: run the ingest pipeline as a background job with polling.

Endpoints:
  GET  /api/ingest/companies  — configured companies (slug, name, website, in_db)
  POST /api/ingest/run        — start a background scrape job
  GET  /api/ingest/status     — poll running/last job progress
"""
from __future__ import annotations

import threading
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import SessionLocal
from app.models import Company
from app.ingest.config import COMPANIES, all_slugs, get_company
from app.ingest.pipeline import run_all, summarize
from app.ingest.cli import build_parser  # validates source choices indirectly

router = APIRouter()


# ---------------------------------------------------------------- job state

class JobState:
    """Single-worker job state (matches the CLI's one-at-a-time model)."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.running = False
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.log: list[dict] = []
        self.summary: dict = {}

    def add(self, level: str, message: str):
        self.log.append({
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": level,
            "message": message,
        })
        # Keep the buffer bounded
        if len(self.log) > 500:
            del self.log[: len(self.log) - 500]


_job = JobState()
_job_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_job(slugs: list[str] | None, sources: tuple[str, ...], dry_run: bool):
    """Thread body — never raises; captures everything into _job."""
    try:
        _job.add("info", f"Starting scrape: sources={list(sources)} "
                         f"companies={slugs or 'ALL'} dry_run={dry_run}")
        stats = run_all(slugs=slugs, sources=sources, dry_run=dry_run)
        for s in stats:
            level = "error" if s.errors else "success"
            _job.add(level, (
                f"{s.company}: brands+{s.brands_created} products+{s.products_created} "
                f"skus+{s.skus_created}/~{s.skus_updated} regions+{s.regions_created} "
                f"distributors+{s.distributors_created} prices+{s.price_records} "
                f"changes+{s.change_events} review+{s.review_items} sources+{s.sources}"
                + (f" | ERRORS: {'; '.join(s.errors)}" if s.errors else "")
            ))
        _job.summary = summarize(stats)
        _job.add("info", f"Done. {_job.summary}")
        if dry_run:
            _job.add("info", "Dry-run: all DB writes were rolled back.")
    except Exception as e:
        _job.add("error", f"Job failed: {e}")
        _job.add("error", traceback.format_exc(limit=5))
    finally:
        _job.running = False
        _job.finished_at = _now()


# ---------------------------------------------------------------- schemas

class RunRequest(BaseModel):
    companies: list[str] | None = None   # None / empty → all
    sources: list[str] = ["website", "report"]  # subset of website|report
    dry_run: bool = False


# ---------------------------------------------------------------- endpoints

@router.get("/companies")
def list_ingest_companies():
    """Configured scraper targets + whether each slug exists in the DB."""
    db = SessionLocal()
    try:
        db_slugs = {c.slug for c in db.query(Company).all()}
    finally:
        db.close()
    return [
        {
            "slug": c.slug,
            "name": c.name,
            "website": c.website,
            "has_website": bool(c.website),
            "has_report": bool(getattr(c, "report_urls", None) or getattr(c, "ir_paths", None)),
            "in_db": c.slug in db_slugs,
        }
        for c in COMPANIES
    ]


@router.post("/run")
def start_run(req: RunRequest):
    valid_sources = {"website", "report"}
    sources = tuple(s for s in req.sources if s in valid_sources) or ("website", "report")

    slugs = req.companies or None
    if slugs:
        unknown = [s for s in slugs if get_company(s) is None]
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown company slug(s): {', '.join(unknown)}. Valid: {', '.join(all_slugs())}")

    if _job.running:
        raise HTTPException(status_code=409, detail="A scrape job is already running. Poll /api/ingest/status.")

    with _job_lock:
        if _job.running:  # double-check under lock
            raise HTTPException(status_code=409, detail="A scrape job is already running.")
        _job.reset()
        _job.running = True
        _job.started_at = _now()
        t = threading.Thread(target=_run_job, args=(slugs, sources, req.dry_run), daemon=True)
        t.start()

    return {"started": True, "dry_run": req.dry_run, "sources": list(sources), "companies": slugs or "all"}


@router.get("/status")
def job_status():
    return {
        "running": _job.running,
        "started_at": _job.started_at,
        "finished_at": _job.finished_at,
        "log": _job.log,
        "summary": _job.summary,
    }
