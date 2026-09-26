#!/bin/sh
set -e
echo "Running alembic upgrade head..."
alembic upgrade head || {
  echo "Alembic failed; falling back to create_all"
  python -c "from app.db import get_engine, Base; from app import models; Base.metadata.create_all(get_engine())"
}
echo "Seeding enterprise data..."
python -c "from app.db import session_scope; from app.seed import seed_enterprise
with session_scope() as s:
    print(seed_enterprise(s))
"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
