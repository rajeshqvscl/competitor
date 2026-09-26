import os

import python_multipart  # noqa: F401 — needed for file uploads
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import (
    companies, categories, retailers, analysis, search, dashboard,
    sources, export, price_history, changes, analyses, ai_search,
    alerts, data_quality, review_queue, distributors, ingest, import_csv, scan
)

app = FastAPI(
    title="Dairy Competitor Intelligence Platform",
    version="0.1.0",
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:9000,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(retailers.router, prefix="/api/retailers", tags=["retailers"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(price_history.router, prefix="/api/prices", tags=["price-history"])
app.include_router(changes.router, prefix="/api/changes", tags=["changes"])
app.include_router(analyses.router, prefix="/api/analyses", tags=["saved-analyses"])
app.include_router(ai_search.router, prefix="/api/ai-search", tags=["ai-search"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(data_quality.router, prefix="/api/data-quality", tags=["data-quality"])
app.include_router(review_queue.router, prefix="/api/review-queue", tags=["review-queue"])
app.include_router(distributors.router, prefix="/api/distributors", tags=["distributors"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(import_csv.router, prefix="/api/import", tags=["import"])
app.include_router(scan.router, prefix="/api/scan", tags=["scan"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
