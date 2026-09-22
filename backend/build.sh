#!/usr/bin/env bash
# Render build script for the backend.
# Runs migrations, then seeds only on the very first deploy
# (when the ownership_types table doesn't exist yet).

set -euo pipefail

echo "Running migrations..."
python -m alembic upgrade head

echo "Checking if database needs seeding..."
python - <<'PY'
from app.db import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT EXISTS ("
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='ownership_types')"
    )).scalar()
if not result:
    print("Database is empty, seeding...")
    import seed
    seed.seed()
else:
    print("Database already seeded, skipping.")
PY

echo "Build complete."
