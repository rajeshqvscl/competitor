# Ingest pipeline — websites + annual reports → Postgres

CLI-driven pipeline that scrapes company websites and annual-report PDFs for the
15 dairy companies, then upserts into the existing schema with provenance.

## Setup

```bash
cd backend
pip install -r requirements.txt

# .env (see .env.example)
GROQ_API_KEY=gsk_...          # https://console.groq.com/keys
INGEST_LLM_ENABLED=true
INGEST_LLM_MODEL=llama-3.3-70b-versatile
DATABASE_URL=postgresql://...
```

LLM is **optional** — without a key, rules-only extraction runs and low-confidence
items go to `review_queue`. With Groq, unmatched report sections get an LLM pass.

## Commands

```bash
cd backend

# List configured companies
python -m app.ingest.cli --list

# Dry-run: extract one company, print stats, roll back DB writes
python -m app.ingest.cli --company heritage-foods --source all --dry-run

# Ingest website only (one company)
python -m app.ingest.cli --company amul --source website

# Annual reports only
python -m app.ingest.cli --company nestle-india --source report

# Everything (all 15, website + reports) — cron entry point
python -m app.ingest.run

# Smoke tests (no network/DB needed)
python -m app.ingest.tests_smoke
```

## How it works

```
config.py (15 companies: website, ir_paths, product_paths)
    │
    ├─ website: sitemap + about/product/distributor pages
    │     → JSON-LD / CSS card extraction (generic.py)
    │
    └─ report: IR page → PDF download (pdf.py)
          → pdfplumber text/tables (pdf_text.py)
          → rule section parsers (rules.py)
          → LLM fallback if low confidence (llm.py, needs OPENAI_API_KEY)
                │
                ▼
         normalize.py → RawPayload
                │
                ▼
         loader.py → upsert + sources + change_events + review_queue
```

### Provenance & review

- Every created brand/product/SKU gets a `sources` row (`source_url`, `confidence`).
- Price/field changes emit `change_events` (visible in `/changes` frontend page).
- Ambiguous items (unknown taxonomy, missing brand, low-confidence extraction)
  go to `review_queue` → approve/reject in `/admin/review`.

### LLM mode (hybrid, default = Groq)

- Rules first; if `INGEST_LLM_ENABLED=true` **and** `GROQ_API_KEY` set,
  unmatched report sections go to Groq (`llama-3.3-70b-versatile`) with a strict JSON schema.
- Base URL: `https://api.groq.com/openai/v1` (OpenAI-compatible — uses `openai` package).
- OpenAI works too: leave `GROQ_API_KEY` empty, set `OPENAI_API_KEY` + `OPENAI_BASE_URL`.
- LLM failures are silent (pipeline continues with rules-only results).

### Where report PDFs come from

| Source | Config field |
|---|---|
| IR page scrape for `*.pdf` links | `CompanyCfg.ir_paths` |
| Pinned direct PDF URL (preferred when known) | `CompanyCfg.report_urls` |

Known IR / AR locations (updated in `config.py`):

| Company | IR page / notes |
|---|---|
| Nestlé India | `nestle.in/investors/stockandfinancials/annualreports` + pinned AR PDF |
| Heritage Foods | `heritagefoods.in/annualreport` + pinned AR 2024-25 PDF |
| Britannia | `britannia.co.in/investors/financial-performance/annual-report` + pinned AR |
| Dodla Dairy | `dodladairy.com/investor-corner/annual-reports` + pinned AR 2023-24 |
| Hatsun Agro | `hap.in/annual-report.php` + pinned AR 2023 PDF |
| Mother Dairy | private (NDDB) — Annual Return PDF pinned |
| Amul / Verka / Milma / Nandini / Warana / Dudhsagar / Govardhan | cooperatives — no stable public AR PDF; website/about pages only |
| Parag / Akshayakalpa | domain corrected (`paragmilkfoods.com`, `akshayakalpa.org`) |

Pin newer AR PDFs into `report_urls` when a new FY is published (yearly).

## Scheduling (Render Cron Job)

1. Render Dashboard → your backend service → **New → Cron Job**
2. Command: `python -m app.ingest.run`
3. Schedule: e.g. `0 6 * * 1` (Mondays 06:00 UTC) or daily
4. Env vars required on the job: `DATABASE_URL`, `GROQ_API_KEY` (optional),
   `INGEST_RATE_MS`, `INGEST_LLM_ENABLED`

Local cron (Linux):

```cron
0 6 * * 1 cd /path/to/backend && . venv/bin/activate && python -m app.ingest.run
```

## Config notes

- `config.py` — website domains, `ir_paths`, pinned `report_urls` per company.
- Site-specific CSS selectors → `CompanyCfg.overrides`.
- PDF cache: `backend/cache/reports/` (gitignored).

## New dependencies

`beautifulsoup4`, `lxml`, `pdfplumber`, `openai` — added to `requirements.txt`.
No separate `groq` package needed — Groq is consumed via the OpenAI-compatible client.
