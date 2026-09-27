#!/usr/bin/env bash
# Run DB-backed pytest against isolated ef-db-test — never Coolify prod.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.test.yml)
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE=(sudo docker compose -f docker-compose.test.yml)
fi

echo "Starting isolated test DB (ef-db-test on :5433)..."
"${COMPOSE[@]}" up -d
for i in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T db-test pg_isready -U enterpriseflow -d enterpriseflow_test >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://enterpriseflow:ef_test_only@127.0.0.1:5433/enterpriseflow_test}"
export EF_DB_TESTS=1
export EF_JWT_SECRET="${EF_JWT_SECRET:-test-jwt-secret-not-for-prod-32c}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6380/0}"
# refuse accidental prod overrides
case "$DATABASE_URL" in
  *enterpriseflow_test*) ;;
  *)
    echo "ERROR: DATABASE_URL must target enterpriseflow_test (got: $DATABASE_URL)" >&2
    exit 2
    ;;
esac

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "Migrating isolated test DB..."
alembic upgrade head

echo "Running pytest against $DATABASE_URL"
pytest -q "$@"
echo "OK — tests finished on isolated DB"
