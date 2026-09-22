# Dairy Competitor Intelligence Platform

A specialized competitive-intelligence platform for the dairy industry.

## Quick Start

### 1. Set up Neon PostgreSQL

1. Go to https://neon.tech and create a free account
2. Create a project named `dairy-competitor`
3. Copy the **pooled connection string** from the dashboard
4. Update `backend/.env` with your connection string:

```
DATABASE_URL=postgresql://neondb_owner:xxxx@ep-xxx.us-east-1.aws.neon.tech/dairy_competitor?sslmode=require
```

### 2. Set up Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 9001
```

### 3. Set up Frontend

```bash
cd frontend
npm install
npm run dev -- -p 9000
```

### 4. Open

- Frontend: http://localhost:9000
- Backend API: http://localhost:9001
- API Docs: http://localhost:9001/docs

## Project Structure

```
competitor/
├── backend/           # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── models/    # SQLAlchemy models (20 tables)
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── api/       # Route handlers (20 endpoints)
│   │   └── services/  # Business logic
│   ├── alembic/       # Database migrations (4 versions)
│   └── seed.py        # Database seeder
├── frontend/          # Next.js + Tailwind
│   └── src/
│       ├── app/       # 13 pages
│       ├── components/# 4 reusable components
│       └── lib/       # API client
├── data/              # 10 seed CSVs
└── docker-compose.yml # Redis only
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/companies` | List companies with filters |
| `GET /api/companies/{id}` | Company detail |
| `GET /api/companies/{id}/competitors` | Find competitors |
| `POST /api/analysis/competitors` | Competitor discovery |
| `POST /api/analysis/portfolio` | Portfolio comparison |
| `POST /api/analysis/sku-comparison` | SKU comparison |
| `POST /api/analysis/retailer-overlap` | Retailer overlap |
| `POST /api/analysis/white-space` | Category gaps |
| `GET /api/distributors` | List distributors |
| `GET /api/distributors/company/{id}` | Company distributors |
| `GET /api/prices/sku/{id}` | SKU price history |
| `GET /api/changes` | Change detection |
| `POST /api/analyses` | Save analysis |
| `POST /api/ai-search` | Natural language search |
| `GET /api/alerts` | Alert subscriptions |
| `GET /api/data-quality` | Data quality metrics |
| `GET /api/review-queue` | Admin review queue |
| `POST /api/export/portfolio` | Export portfolio CSV |
| `POST /api/export/sku-comparison` | Export SKU CSV |
| `GET /api/sources/{type}/{id}` | Evidence/sources |

## Seed Data

- 15 dairy companies (Amul, Mother Dairy, Nestle, Heritage, Verka, etc.)
- 24 brands, 58 products, 95+ SKUs
- 12 retailers, 17 distributors
- 8 categories, 33 subcategories
- 4 regions + 14 states
