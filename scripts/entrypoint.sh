#!/bin/sh
set -e
echo "Running alembic upgrade head..."
alembic upgrade head || {
  echo "Alembic failed; falling back to create_all"
  python - <<'PY'
from sqlalchemy import text
from app.db import get_engine, Base, session_scope
from app import models
engine = get_engine()
with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
Base.metadata.create_all(engine)
print("create_all done")
PY
}
echo "Seeding enterprise data..."
python - <<'PY'
from sqlalchemy import text
from app.db import session_scope
from app.seed import seed_enterprise
from app.rag.service import ingest_directory
with session_scope() as s:
    s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    print("seed", seed_enterprise(s))
    print("rag", ingest_directory(s))
PY
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
